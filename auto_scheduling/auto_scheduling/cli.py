"""Command line entry point (inputs always from SQL Server views sched.vw_engine_*, same as the web).

    python -m auto_scheduling load-inputs --stores 2189,2030 --week 2026-11-16 --tcph 2189=5.75
    python -m auto_scheduling run      --stores 2189,2184,2030 --week 2026-11-09
    python -m auto_scheduling check    --store 2184 --week 2026-11-09 --allow-past-weeks
    python -m auto_scheduling schedule --stores 2189,2184,2030 --week 2026-11-09 --allow-past-weeks --export-file2
"""
from __future__ import annotations

import argparse
import sys

from .config import DEFAULT_CONFIG, REPORTS_DIR
from .pipeline import RunResult, SqlSource, prepare_store_week, run_store_week
from .timeutil import WEEKDAYS, to_date


def _paths(args) -> SqlSource:
    """SQL Server views; --availability-week (default SCHED_DEFAULT_AVAILABILITY_WEEK) = busy-data week reused (back-test)."""
    from .settings import get_settings

    aw = getattr(args, "availability_week", None) or get_settings().default_availability_week
    return SqlSource(availability_week=to_date(aw) if aw else None)


def _cmd_load_inputs(args) -> int:
    """Load Availability Files + OPS targets into the dbo input tables (owned by the ASP.NET app)."""
    from .config import DATA_DIR
    from .db import get_engine
    from .etl.load_inputs import load_store_workbook, upsert_ops_config
    from .inputs.availability_file import default_availability_path

    sys.stdout.reconfigure(encoding="utf-8")
    eng = get_engine()
    week = to_date(args.week) if args.week else None
    lines = [f"# DQ report · load-inputs · tuần lịch bận {week or '—'}", ""]
    for sid in [s.strip() for s in (args.stores or "").split(",") if s.strip()]:
        path = default_availability_path(DATA_DIR, sid)
        rep = load_store_workbook(eng, sid, path, None if args.employees_only else week)
        lines += rep.lines() + [""]
    if args.tcph:
        targets = {k.strip(): float(v) for k, v in (p.split("=") for p in args.tcph.split(","))}
        lines += ["## ops_store_config"] + [f"- {x}" for x in upsert_ops_config(eng, targets, delete_store_codes=tuple(
            s.strip() for s in (args.delete_config or "").split(",") if s.strip()))] + [""]
    out = DATA_DIR / "out" / "load_inputs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "dq_report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print(f"report: {out / 'dq_report.md'}")
    return 0


def _cmd_run(args) -> int:
    """Platform run: SQL inputs -> engine -> sched.Schedule* (+ sched.engine_run log), same path as the web UI."""
    from .service import run_and_store
    from .settings import get_settings

    aw = args.availability_week or get_settings().default_availability_week
    rc = 0
    for sid in [s.strip() for s in args.stores.split(",") if s.strip()]:
        out = run_and_store(sid, to_date(args.week), to_date(aw) if aw else None)
        print(f"store {sid} week {args.week}: run {out['run_id']} {out['status']} "
              + (f"· {out.get('assessment')} · {out.get('counts')}" if out["status"] == "done" else f"· {out.get('error')}"))
        rc |= out["status"] != "done"
    return rc


def _cmd_check(args) -> int:
    cfg = DEFAULT_CONFIG.with_overrides(allow_past_weeks=args.allow_past_weeks or None,
                                        forecast_quantile=args.quantile)
    week = to_date(args.week)
    swi, issues = prepare_store_week(args.store, week, cfg, _paths(args))

    print(f"== store {args.store} week {week} (quantile {cfg.forecast_quantile}) ==")
    if swi is not None:
        s, cal = swi.store, swi.calendar
        print(f"hours {s.hours_label} | window {cal.window_hours:g}h | slots/day {len(cal.operating_hours)} | "
              f"tcph_target {s.tcph_target:g} (band {s.tcph_target:g}-{s.tcph_ceiling:.2f})")
        print(f"employees {len(swi.employees)} (manager-group {sum(e.counts_as_mod for e in swi.employees)}, "
              f"FT {sum(e.employment_type == 'FT' for e in swi.employees)}, PT {sum(e.employment_type == 'PT' for e in swi.employees)}) "
              f"| busy rows {len(swi.busy)} | shift codes {len(swi.shift_codes)} | source {swi.employee_source}")
        d = swi.daily.copy()
        d.insert(1, "dow", [WEEKDAYS[x.weekday()] for x in d["date"]])
        cols = ["date", "dow", "day_type", "adtc", "required_staff_hours", "band_min_hours", "band_max_hours",
                "floor_hours", "max_achievable_tcph", "target_feasible", "peak_required"]
        print(d[cols].round(2).to_string(index=False))
        print("peak windows:", ", ".join(f"{w.date:%a} {w.start_hour:02d}-{w.end_hour:02d}" for w in swi.peak_windows) or "none")

        out_dir = REPORTS_DIR / f"check_{args.store}_{week:%Y%m%d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        swi.demand.to_csv(out_dir / "slot_demand.csv", index=False)
        swi.daily.to_csv(out_dir / "daily_demand.csv", index=False)
        issues.to_frame().to_csv(out_dir / "issues.csv", index=False)
        print(f"outputs: {out_dir}")

    print(f"-- issues: {issues!r}")
    for i in issues:
        if i.severity != "INFO" or args.verbose:
            print(f"[{i.severity}] {i.code}: {i.message}")
    blocked = issues.has_critical()
    print("RESULT:", "BLOCKED (CRITICAL issues)" if blocked else "READY for optimizer")
    return 1 if blocked else 0


def print_run_summary(res: RunResult, verbose: bool = False) -> None:
    issues = res.issues
    print(f"\n== store {res.store_id} week {res.week_start} ==")
    if res.blocked:
        print("BLOCKED before optimising:")
        for i in issues:
            if i.severity == "CRITICAL":
                print(f"  [CRITICAL] {i.code}: {i.message}")
        return
    swi, k = res.swi, res.kpi
    s = swi.store
    print(f"hours {s.hours_label} | tcph_target {s.tcph_target:g} (band {s.tcph_target:g}-{s.tcph_ceiling:.2f}) | "
          f"employees {len(swi.employees)} | source {swi.employee_source}")
    print(f"planning status: {k.planning_status} ({k.status_label}) | weekly TCPH {k.weekly_tcph if k.weekly_tcph is None else round(k.weekly_tcph, 2)} "
          f"{'in band' if k.tcph_in_band else 'OUT of band'} | utilization {k.utilization and round(k.utilization, 2)} ({k.utilization_status}) | "
          f"coverage {k.coverage_pct:.1f}% ({k.coverage_status}) | MOD coverage {k.manager_coverage_pct:.1f}% ({k.manager_coverage_status})")
    d = res.daily_kpi[res.daily_kpi["status"] == "OPEN"]
    cols = ["date", "weekday", "adtc", "labor_reg", "labor_train", "labor_nso", "tcph", "tcph_in_band", "band_min_hours", "band_max_hours",
            "required_hours", "scheduled_hours", "staff_gap_hours", "manager_gap_slots", "overstaff_hours"]
    print(d[cols].round(2).to_string(index=False))
    print("\nroster (hours/week):")
    print(res.grid.to_string(index=False))
    counts = {s_: sum(1 for i in issues if i.severity == s_) for s_ in ("CRITICAL", "WARNING", "INFO")}
    print(f"\nissues: {counts}")
    for i in issues:
        if i.severity == "CRITICAL" or (i.severity == "WARNING" and verbose) or (verbose and i.severity == "INFO"):
            print(f"  [{i.severity}] {i.code}: {i.message}")
    if not verbose:
        by_code = {}
        for i in issues:
            if i.severity == "WARNING":
                by_code.setdefault(i.code, []).append(i)
        for code, lst in by_code.items():
            print(f"  [WARNING] {code} x{len(lst)}: {lst[0].message}" + (" ..." if len(lst) > 1 else ""))
    if k.recommendations:
        print("recommendations:")
        for rec in k.recommendations:
            print(f"  - {rec['text']}")
    if res.file2_errors:
        print("File 2 BLOCKED:\n  " + "\n  ".join(res.file2_errors[:20]))
    print("outputs:")
    for name, p in res.files.items():
        print(f"  {name}: {p}")


def _cmd_schedule(args) -> int:
    cfg = DEFAULT_CONFIG.with_overrides(allow_past_weeks=args.allow_past_weeks or None, forecast_quantile=args.quantile,
                                        tcph_priority=args.priority)
    week = to_date(args.week)
    stores = [s.strip() for s in args.stores.split(",") if s.strip()]
    rc = 0
    for sid in stores:
        res = run_store_week(sid, week, cfg, _paths(args), export_file2=args.export_file2)
        print_run_summary(res, verbose=args.verbose)
        if args.to_db:
            from .db import get_engine
            from .output.db_writer import write_run
            try:
                replaced, counts = write_run(res, cfg, engine=get_engine(args.db_conn))
                action = "replaced the previous roster" if replaced else "written"
                print(f"DB: store {sid} week {week} {action}: " + ", ".join(f"{t} {n}" for t, n in counts.items()))
            except Exception as exc:  # report and continue with the next store
                print(f"DB: write FAILED for store {sid}: {exc}")
                rc = 1
        if res.blocked or (res.kpi and res.kpi.planning_status == "CRITICAL"):
            rc = 1
    return rc


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(prog="auto_scheduling")
    sub = p.add_subparsers(dest="cmd", required=True)

    li = sub.add_parser("load-inputs", help="load Availability Files + OPS targets into dbo input tables (SQL Server)")
    li.add_argument("--stores", default="", help="stores whose data/Availability File {store}.xlsx is loaded, e.g. 2189,2030")
    li.add_argument("--week", default=None, help="Monday of the availability week, e.g. 2026-11-16")
    li.add_argument("--employees-only", action="store_true", help="only upsert dim_employee")
    li.add_argument("--tcph", default="", help="OPS targets, e.g. 2189=5.75,2184=6.08,2030=5.64")
    li.add_argument("--delete-config", default="", help="store codes whose ops_store_config row is removed (test rows)")
    li.set_defaults(func=_cmd_load_inputs)

    ru = sub.add_parser("run", help="platform run: SQL inputs -> engine -> sched tables (logged in sched.engine_run)")
    ru.add_argument("--stores", required=True)
    ru.add_argument("--week", required=True, help="week_start, Monday YYYY-MM-DD")
    ru.add_argument("--availability-week", default=None, help="busy-data week reused for back-test (default SCHED_DEFAULT_AVAILABILITY_WEEK)")
    ru.set_defaults(func=_cmd_run)

    def common(sp):
        sp.add_argument("--week", required=True, help="week_start, Monday YYYY-MM-DD")
        sp.add_argument("--allow-past-weeks", action="store_true", help="dev / back-test only")
        sp.add_argument("--quantile", default=None, help="tc_p50 (default) / tc_p75 / ...")
        sp.add_argument("--availability-week", default=None,
                        help="Monday of the busy-data week reused for the schedule week (back-test); default SCHED_DEFAULT_AVAILABILITY_WEEK")
        sp.add_argument("-v", "--verbose", action="store_true", help="also print WARNING/INFO issues")

    c = sub.add_parser("check", help="load + validate inputs and build demand for one store-week")
    c.add_argument("--store", required=True)
    common(c)
    c.set_defaults(func=_cmd_check)

    s = sub.add_parser("schedule", help="full flow: pre-flight + greedy + validation + outputs for store-weeks")
    s.add_argument("--stores", required=True, help="comma-separated store ids, e.g. 2189,2184,2030")
    s.add_argument("--priority", choices=["band_first", "coverage_first"], default=None)
    s.add_argument("--export-file2", action="store_true", help="also write File 2 (Upload Phan Cong); back-test weeks get a warning")
    s.add_argument("--to-db", action="store_true",
                   help="write the suggested roster to SQL Server tables Schedule* (replaces the store-week if it exists)")
    s.add_argument("--db-conn", default=None, help="ADO.NET or ODBC connection string (default: SCHED_SQL_CONN in .env)")
    common(s)
    s.set_defaults(func=_cmd_schedule)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
