"""Review workbook for the pilot (one xlsx per store-week): roster grid, coverage heat table,
daily KPI, validation issues, recommendations. Not an upload file - for humans."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

FILL = {"MANAGER_GAP": "F4B6B6", "STAFF_GAP": "FAD7A0", "OVERSTAFF": "D6EAF8", "OK": "D5F5E3",
        "CRITICAL": "F4B6B6", "WARNING": "FCF3CF", "INFO": "FFFFFF"}


def _autosize(ws, min_w: int = 6, max_w: int = 60) -> None:
    for col in ws.columns:
        width = max((len(str(c.value)) for c in col if c.value is not None), default=0)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(min_w, min(max_w, width + 2))


def write_review_workbook(path: Path, grid: pd.DataFrame, coverage: pd.DataFrame, daily: pd.DataFrame,
                          issues: pd.DataFrame, kpi: dict, recommendations: list[dict], schedule: pd.DataFrame) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as xw:
        summary = pd.DataFrame([{"metric": k, "value": v} for k, v in kpi.items()])
        summary.to_excel(xw, sheet_name="Summary", index=False)
        pd.DataFrame(recommendations or [{"text": "none"}]).to_excel(xw, sheet_name="Summary", index=False, startrow=len(summary) + 3)
        grid.to_excel(xw, sheet_name="Roster", index=False)
        piv = coverage.pivot(index="slot", columns="date", values="status")
        req = coverage.pivot(index="slot", columns="date", values="required_staff")
        sch = coverage.pivot(index="slot", columns="date", values="scheduled_staff")
        mod = coverage.pivot(index="slot", columns="date", values="scheduled_manager")
        txt = req.astype(str)
        for c in piv.columns:
            txt[c] = [f"{int(s)}/{int(q)} M{int(m)}" for s, q, m in zip(sch[c], req[c], mod[c])]
        txt.columns = [f"{c:%a %d/%m}" for c in txt.columns]
        txt.index = [f"{int(h):02d}:00" for h in txt.index]
        txt.to_excel(xw, sheet_name="Coverage")
        daily.to_excel(xw, sheet_name="Daily KPI", index=False)
        issues.to_excel(xw, sheet_name="Issues", index=False)
        schedule.to_excel(xw, sheet_name="Schedule", index=False)
        coverage.to_excel(xw, sheet_name="Slot coverage", index=False)

        wb = xw.book
        ws = wb["Coverage"]
        ws.cell(row=1, column=1, value="scheduled/required  M=MOD")
        status = piv.to_numpy()
        for i in range(status.shape[0]):
            for j in range(status.shape[1]):
                cell = ws.cell(row=i + 2, column=j + 2)
                cell.fill = PatternFill("solid", fgColor=FILL.get(str(status[i, j]), "FFFFFF"))
                cell.alignment = Alignment(horizontal="center")
        ws_i = wb["Issues"]
        sev_col = list(issues.columns).index("severity") + 1 if "severity" in issues.columns else None
        if sev_col:
            for row in range(2, ws_i.max_row + 1):
                sev = ws_i.cell(row=row, column=sev_col).value
                fill = FILL.get(str(sev))
                if fill and fill != "FFFFFF":
                    for col in range(1, ws_i.max_column + 1):
                        ws_i.cell(row=row, column=col).fill = PatternFill("solid", fgColor=fill)
        ws_r = wb["Roster"]
        for row in ws_r.iter_rows(min_row=2):
            for cell in row:
                if isinstance(cell.value, str) and cell.value.endswith("*"):
                    cell.font = Font(bold=True)
                elif cell.value == "OFF":
                    cell.font = Font(color="999999")
                elif cell.value == "AL":
                    cell.fill = PatternFill("solid", fgColor="E8DAEF")
        for name in ("Summary", "Roster", "Coverage", "Daily KPI", "Issues", "Schedule", "Slot coverage"):
            _autosize(wb[name])
            wb[name].freeze_panes = "B2" if name in ("Roster", "Coverage") else "A2"
    return path
