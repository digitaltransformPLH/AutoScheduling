# PLH Auto Scheduling — SPEC v0.3

> **Status:** Draft for review · **Owner:** Edward (PM) · **Last updated:** 12-Nov-2026 (v0.3: band-first, per-store opening hours, 24h stores, shift-code pre-flight)
> **Source:** Notion page *Auto scheduling* + logic reverse-engineered from `PLH_Weekly_Workforce_Planning_Oct2026.html` (class `WeeklySchedulingEngine`, `ExportModule`).
> Items tagged **[DECISION dd-Mmm-2026]** override the demo behaviour; **[PROPOSED]** = awaiting confirmation.
> **How to use:** save as `SPEC.md` at the repo root and ask Claude Code to implement phase by phase (Section 10).

---

## 0. Scope

Build a weekly auto-scheduling engine for one store-week at a time:

```
forecast_tc_hourly (Giang, tc_p50) ──┐
dim_store / ops_store_config ───────┼─► Demand (required headcount per slot)
dim_employee + busy (availability) ──┘            │
                                                  ▼
                                    Optimizer (v0 greedy → v1 CP-SAT)
                                                  │
                          ┌───────────────────────┼────────────────────────┐
                          ▼                       ▼                        ▼
                    schedule table         slot_coverage / daily_kpi   File 2: attendance upload
```

**In scope (v0/v1):** demand calculation, roster + assignment, validation, KPI, attendance upload file.
**Out of scope for now:** any forecast calculation (day factors, holiday/double-day uplift, hourly profiles — all handled inside Giang's model), task/station-level workload (Step 2), channel-level staffing (dine-in vs delivery columns are available but unused), discrete-event simulation, cup-based demand driver, Planning file (File 1) export, Google Sheet publish.

---

## 1. Decision log

| Date | Decision | Impact |
|---|---|---|
| 05-Nov-2026 | FT/Manager shift = 8 working hours, **no break** inside the shift | H04 |
| 05-Nov-2026 | Regular PT: **no** weekly hour cap, no days/week cap (HR/Legal to recheck before go-live) | `PT_REGULAR_WEEKLY_CAP = None` |
| 05-Nov-2026 | **No** minimum rest between consecutive shifts (HR/Legal to recheck) | `MIN_REST_BETWEEN_SHIFTS = None` |
| 05-Nov-2026 | ~~Peak-hour coverage has priority over the TCPH band~~ — **superseded 12-Nov-2026** | — |
| 05-Nov-2026 | ≥ 1 MOD on floor during **all** opening hours | H11 |
| 05-Nov-2026 | **AL does not replace the weekly OFF.** FT/Manager always get 1 OFF; AL only on the 6 working days | H08 |
| 05-Nov-2026 | Setup 30' / cleaning 30' apply to all stores (except 24h stores, see 12-Nov) | `SETUP_MINUTES = CLEAN_MINUTES = 30` (config) |
| 05-Nov-2026 | Min 2 staff/slot and Open/Close = 2 are chain-wide | ops_store_config defaults |
| 11-Nov-2026 | Keep demo 60-min slots (accept the :30 offset) | Section 4.3 |
| 11-Nov-2026 | Drop the demo day-factor engine | Section 5.1 |
| 11-Nov-2026 | Week deadline enforced server-side; **no scheduling for weeks ≤ current week** | Section 8.4 |
| 12-Nov-2026 | **Use Giang's `forecast_tc_hourly` as-is** (store × date × hour TC). Holiday / double-day effects are already in the model: no uplift, no day-type logic, no re-normalisation | Sections 2, 5.1 |
| 12-Nov-2026 | **TCPH target is an OPS input per store** (`ops_store_config.tcph_target`), not a chain-wide 8 | Sections 2, 5.2 |
| 12-Nov-2026 | **Back to band-first (demo logic):** the TCPH band is the top objective; coverage gaps are accepted to stay in band, except the hard floor rules H01–H13. Peak-coverage hard rule (old H14) removed | Sections 3, 6 |
| 12-Nov-2026 | Opening/closing time **per store from `dim_store`** (mandatory); no chain default | Sections 2, 4.2, 5.1 |
| 12-Nov-2026 | **MOD: at least 1 manager-group per slot; 2+ overlapping is fine.** Add manager-group shifts beyond open/close when the day is longer than 16h | Section 4.4, H11 |
| 12-Nov-2026 | **24h stores stay in scope**; no setup/cleaning windows for them | Section 4.5 |
| 12-Nov-2026 | Shift-code check moved to a **pre-flight**: only shifts with a valid attendance code can be generated | Sections 6.0, 7.3 |
| 12-Nov-2026 | `ALLOW_PAST_WEEKS` flag for dev / back-test runs on past forecast weeks | Section 8.4 |
| 12-Nov-2026 | **24h stores: an employee who worked the overnight shift cannot work a morning shift the next day** | Section 4.5, H17 |
| 12-Nov-2026 | `forecast_tc_hourly` is a DB table (system source), removed from the manual input list; `ops_input` renamed to **`ops_store_config`** | Sections 2, 2.1 |
| 13-Nov-2026 | Slot status **OVERSTAFF only when scheduled > required_staff** (whole people); fractional overstaff stays an efficiency metric | Section 5.3 |
| 13-Nov-2026 | **Use forecast only inside opening hours**; TC outside them is ignored (INFO for audit, no warning) | Section 5.1 |

---

## 2. Input contracts

| Table | Columns | Notes |
|---|---|---|
| `dim_store` | store_id (= forecast store_id, string e.g. "2001"), short_name, opening_time, closing_time, is_24h, closed_sat, closed_sun | **opening_time / closing_time mandatory per store** (07:00 / 22:00 only for mock data). No setup/clean columns: setup and cleaning are fixed at 30' for every store (config), 0 when is_24h |
| `dim_employee` | employee_id, store_id, name, position, employment_type (FT/PT), labor_group (Regular/Training/NSO), status | labor_group mandatory |
| `busy` | employee_id, weekday (Mon..Sun), busy_from, busy_to | Busy exceptions only; no row = available all week. `busy_from = busy_to = "AL"` → annual leave (FT only) |
| `ops_store_config` | store_id, tcph_target, tcph_ceiling_mult, open_staff, close_staff, min_staff_per_slot | **tcph_target is set per store by OPS — mandatory, no chain default.** Other defaults: 1.05 / 2 / 2 / 2 |
| `dim_shift_code` | shift_code, start, end, duration_hours | From `PLH_Shift_Code_Map.csv` (210 codes). Owner: HR |

**Input validation (fail fast):**
- Missing/invalid labor_group → error `LABOR_GROUP_REQUIRED` / `INVALID_LABOR_GROUP`.
- Inactive/terminated employees excluded; duplicate employee_id → keep first, warn `DUPLICATE_EMPLOYEE_KEY`.
- No manager-group employee in store → error `NO_MANAGER`.
- busy_to ≤ busy_from → error `BAD_BUSY_TIME`; busy rows with unknown employee → warn `ORPHAN_AVAILABILITY_RECORD`.
- dim_store: missing opening/closing time (and not is_24h) → error `STORE_HOURS_MISSING`.
- ops_store_config: missing or ≤ 0 `tcph_target` for a store → error `TCPH_TARGET_MISSING` (store cannot be scheduled).
- Forecast: duplicate (store_id, forecast_date, hour) → error; negative TC → error; week has < 7 dates for an open store → error `FORECAST_MISSING_DAY`; operating hour with no forecast row → TC = 0 + warning `FORECAST_MISSING_HOUR`.

### 2.1 `forecast_tc_hourly` (from Giang) — system table, not a manual input

Read directly from the database table produced by Step 1 (Giang); it is not uploaded or edited by users, so it is not listed in the input table above. The forecast checks in the validation list still apply when the table is read.

Grain: **store_id × forecast_date × hour** (unique). `hour` = slot start, 60-min slot (hour 7 = 07:00–08:00). File observed 12-Nov-2026: 3 weeks (2026-W44 → W46), 261–264 stores/week, method `M9_v1`.

| Column | Type | Used by scheduler | Meaning |
|---|---|---|---|
| store_id | str | **key** | Store code (e.g. "2001" → attendance `PL2001`) |
| forecast_date | date | **key** | Date |
| hour | int 0–23 | **key** | Slot start hour |
| week_start, iso_week | date, str | **filter** | Monday of the planning week; ISO week |
| plan_run_id, created_at | str, timestamp | **filter** | Forecast run; if several runs exist for a week, use the latest `created_at` |
| tc_p50 | float | **demand** | Median forecast TC for the hour (= tc_dine_in + tc_delivery) |
| tc_p25 / p75 / p80 / p90 | float | optional | Prediction-interval quantiles; selectable via `FORECAST_QUANTILE` |
| is_peak | bool | reporting | Model's top-3 hours of the day (exactly 3 per store-day) |
| day_type, event_key | str | passthrough | NORMAL / MEGA (e.g. 11-Nov); already applied in tc — display only |
| day_of_week | int 1–7 | passthrough | 1 = Monday |
| tc_dine_in, tc_delivery | float | future | Channel split (for Step 2 station model) |
| store_age_layer, share_*, event_ratio_*, share_source | mixed | ignore | Model internals |
| actual_tc | float | evaluation only | Actual TC for past dates (WMAPE / back-test); never used for scheduling |
| forecast_origin, forecast_run_id, bill_cutoff_date, method_version | mixed | lineage | Store in output for audit |

---

## 3. Global constants

```python
SLOT_MINUTES = 60                 # keep demo behaviour [DECISION 11-Nov-2026]
FT_SHIFT_HOURS = 8                # 8 working hours, no break [DECISION 05-Nov-2026]
FT_MAX_WEEKLY_HOURS = 48
FT_WORK_DAYS_PER_WEEK = 6         # + exactly 1 OFF when store opens 7 days
PT_MIN_HOURS, PT_MAX_HOURS = 4, 8 # whole hours only
PT_REGULAR_WEEKLY_CAP = None      # [DECISION 05-Nov-2026] - HR/Legal to recheck
SPECIAL_PT_HOURS = 4              # PT in Training/NSO: exactly 4h/day
SPECIAL_PT_DAYS_TARGET = 5
SPECIAL_PT_WEEKLY_MAX = 20
MIN_STAFF_PER_SLOT = 2            # chain-wide [DECISION 05-Nov-2026]
REQUIRED_MANAGER_PER_SLOT = 1     # MOD all opening hours [DECISION 05-Nov-2026]
MIN_REST_BETWEEN_SHIFTS = None    # [DECISION 05-Nov-2026] - HR/Legal to recheck
TCPH_PRIORITY = "band_first"      # [DECISION 12-Nov-2026] demo logic; "coverage_first" kept as an option only
FORECAST_QUANTILE = "tc_p50"      # demand column; p75/p80 possible later (Open question Q13)
ALLOW_PAST_WEEKS = False          # True only for dev / back-test [DECISION 12-Nov-2026]
MAX_MANAGER_GAP_FILL_SHIFTS = 2   # extra manager-group shifts per day beyond open/close (Section 4.4)
MORNING_SHIFT_CUTOFF = "12:00"    # [PROPOSED] H17: a "morning shift" = shift starting before this time
TIMEZONE = "Asia/Ho_Chi_Minh"
```

All constants must live in one config module and be overridable per store via `ops_store_config`.

---

## 4. Rules

### 4.1 Employee classification

- `is_manager`: position matches Store Manager | Assistant Store Manager | Shift Supervisor | "quản lý" | "QL". Rank SM=1, ASM=2, SS=3.
- `can_act_as_manager`: position contains "Barista Trainer". MOD **only** when no eligible manager exists.
- `is_fixed` = employment_type == FT **or** is_manager → 8h shifts + weekly OFF rule.
- `is_special_pt` = PT and labor_group in (Training, NSO).
- **MOD** = a manager-group employee on the floor in a slot (a role in the shift, not a position). Training-group managers never count as MOD.

### 4.2 Time model (per store, from `dim_store`)

- `setup_start = opening − SETUP_MINUTES`; `clean_end = closing + CLEAN_MINUTES`, both fixed at 30' (config, not in `dim_store`) (e.g. 07:00–22:00 → 06:30–22:30; 06:00–22:00 → 05:30–22:30).
- Every shift lies inside `[setup_start, clean_end]`; a shift starting earlier is moved to setup_start.
- **Opener** = shift starting at setup_start. **Closer** = shift ending exactly at clean_end and covering the last slot.
- FT open shift = `setup_start → setup_start + 8h`; FT close shift = `clean_end − 8h → clean_end`.
- Max 1 shift per employee per day; contiguous; no split shifts.
- Shift start/end on the :00/:30 grid and must exist in `dim_shift_code` (pre-flight, Section 6.0).

### 4.3 Slot mapping (demo-compatible) [DECISION 11-Nov-2026]

Operating slots = 60-min slots in `[opening, closing)` of the store (07:00–22:00 → 15 slots; 06:00–22:00 → 16 slots). A shift covers every operating slot with `slot_start ≥ floor_hour(shift_start)` and `slot_end ≤ ceil_hour(shift_end)`.
Example (07:00–22:00 store): 06:30–14:30 covers 07:00–15:00; 14:30–22:30 covers 14:00–22:00. **Known limitation:** coverage at the hand-over hour is overstated. Setup/cleaning windows have no slots.

### 4.4 Manager coverage [DECISION 12-Nov-2026]

- Each open day: 1 manager-group opener + 1 manager-group closer (8h, locked) — H10.
- Every operating slot needs **≥ 1** MOD (H11). **Two or more MODs in the same slot are allowed** (overlap is fine).
- If open + close manager shifts leave slots without a MOD (window `clean_end − setup_start` > 16h, e.g. 05:30–22:30 = 17h, or a manager OFF), add manager-group 8h shifts covering the uncovered slots, up to `MAX_MANAGER_GAP_FILL_SHIFTS` per day. Pick order SM → ASM → SS (fewest weekly hours first), then Barista Trainer fallback. If still uncovered → `MANAGER_GAP` (validation issue, not a crash).
- Capacity check: MOD-hours needed per week ≈ (clean_end − setup_start) × open days (16h × 7 = 112h for a 07:00–22:00 store; 17h × 7 = 119h for 06:00–22:00), while each manager-group employee gives at most 48h (H07). Stores with < 3 manager-group employees (plus Barista Trainers as fallback) cannot cover the week → `INSUFFICIENT_MANAGER_CAPACITY` warning before optimising.

### 4.5 24h stores [DECISION 12-Nov-2026]

- Identified by `dim_store.is_24h = true` (4 stores in the 12-Nov forecast have rows for all 24 hours).
- **No setup/cleaning windows** (setup = clean = 0); operating slots = 00:00–24:00 (24 slots).
- **No opener/closer rules:** H09 and H10 do not apply; manager presence is guaranteed by H11 (≥ 1 MOD every slot, via 4.4).
- [PROPOSED] Shifts may cross midnight (e.g. 22:00–06:00). A shift belongs to its start date; its slots after 00:00 count toward the next day's coverage. Max 1 shift per employee per start date and no overlap with the previous day's shift. Valid shifts are limited by the shift-code pre-flight: the 8h pattern 22:00–06:00 / 06:00–14:00 / 14:00–22:00 is fully coded, but only 6 of 60 possible overnight 4–8h pairs have a code.
- **No morning shift after a night shift** [DECISION 12-Nov-2026] (H17): if an employee's shift on day D crosses midnight, that employee gets no shift on D+1 starting before `MORNING_SHIFT_CUTOFF` (e.g. after 22:00–06:00 on Monday, the 06:00–14:00 shift on Tuesday is not allowed; 14:00–22:00 is). Applies to all employee groups, managers included.
- Week boundary: Monday 00:00–06:00 is covered by the previous week's Sunday overnight shift (read from the previous published roster; if none, those slots are treated as uncovered with warning `PREVIOUS_WEEK_OVERFLOW_MISSING`). The same previous-week roster is used for H17: whoever worked Sunday night cannot take a Monday morning shift. Sunday's overnight shift spills into next Monday and is kept in this week's `schedule` by its start date.

---

## 5. Demand (simulation v0, productivity-driven)

### 5.1 Forecast TC per slot [DECISION 12-Nov-2026]

```python
fc = read_table("forecast_tc_hourly")                       # DB table (Section 2.1)
fc = fc[(fc.store_id == store) & (fc.week_start == week_start)]
fc = fc[fc.created_at == fc.created_at.max()]                 # latest run for that week
fc = fc[(fc.hour >= opening_hour) & (fc.hour < closing_hour)] # opening/closing from dim_store; 24h store keeps 0-23
forecast_tc[date, slot] = fc[FORECAST_QUANTILE]               # used as-is: no uplift, no re-normalisation
is_peak_forecast[date, slot] = fc.is_peak
```

- Holiday / MEGA / double-day effects are **already in the forecast**; `day_type` is display-only.
- Only forecast rows inside the store's opening hours `[opening, closing)` are used. Rows outside them are ignored [DECISION 13-Nov-2026]: logged as INFO `FORECAST_OUTSIDE_OPENING_HOURS` (TC share dropped) for audit only — not a warning, not shown to users.
- Daily TC (ADTC) = Σ forecast_tc over operating slots.

### 5.2 Required headcount

```python
for store, date, slot in operating_slots:
    labor_hours = forecast_tc[slot] / tcph_target          # 60-min slot => labor hours == people
    rounded = floor(labor_hours) if frac(labor_hours) < 0.5 else ceil(labor_hours)
    required_staff = max(MIN_STAFF_PER_SLOT, rounded)
    required_manager = REQUIRED_MANAGER_PER_SLOT
    is_peak_candidate = labor_hours > 2
```

- **MOD is INSIDE required_staff**: required 3 = 1 MOD + 2 staff, never 3 + 1.
- Daily labor budget = Σ forecast_tc / tcph_target. TCPH band ⇒ daily labor hours ∈ [TC / (tcph × 1.05), TC / tcph].
- **Target feasibility check (per store-day, before optimising):** `max_achievable_tcph = TC_day / (min_staff_per_slot × number_of_operating_slots)` — the TCPH reached if the store ran only its 2-person floor all day (independent of the target). If `tcph_target > max_achievable_tcph` → warning `TCPH_TARGET_INFEASIBLE` with both values: the band cannot be met even with a perfect roster. Under band-first this matters most: the optimizer will cut coverage down to the H13 floor and still breach the band.
- **Peak window (demo logic, scoring only):** adjacent slots with labor_hours > 2 form a cluster; merge clusters if gap ≤ 1h and total ≤ 8h; extend to ≥ 4h. Used for FT window scoring (6.4 step 3) and recommendations. The forecast `is_peak` flag (top-3 hours) is passed through to `slot_coverage` for reporting.

### 5.3 Coverage evaluation (per slot)

```python
scheduled_staff   = count(shifts covering slot)               # all labor groups, incl. MOD and NSO
actual_mgr        = count(manager-group, labor_group != Training)
acting_mgr        = count(barista_trainer, labor_group != Training)
scheduled_manager = actual_mgr if actual_mgr > 0 else min(1, acting_mgr)
staff_gap   = max(0, required_staff - scheduled_staff)
manager_gap = max(0, 1 - scheduled_manager)
overstaff   = max(0, scheduled_staff - labor_hours)
status = "MANAGER_GAP" if manager_gap else "STAFF_GAP" if staff_gap else "OVERSTAFF" if scheduled_staff > required_staff else "OK"
# [DECISION 13-Nov-2026] status uses whole people vs the rounded required_staff shown to users (4/4 = OK).
# The fractional `overstaff` above stays as the efficiency metric (objective S03, KPI), not as the slot status.

TCPH_day     = TC_day / (hours_Regular + hours_Training)     # NSO excluded; AL excluded
TCPH_NSO_day = TC_day / hours_all
```

---

## 6. Optimizer

### 6.0 Pre-flight (per store-week, before optimising) [DECISION 12-Nov-2026]

1. Build all candidate shift templates from the store's hours (4.2 / 4.5): fixed 8h, Regular PT 4–8h, special PT 4h, on the :00/:30 grid.
2. Keep only templates whose (start, end) exists in `dim_shift_code`; log dropped templates (`SHIFT_TEMPLATE_NO_CODE`, INFO).
3. If a required template has no code (FT open shift, FT close shift, or no coded 8h template covering a MOD gap) → error `REQUIRED_SHIFT_NO_CODE`; store-week is not scheduled.
4. Run input checks (Section 2), `TCPH_TARGET_INFEASIBLE` (5.2) and `INSUFFICIENT_MANAGER_CAPACITY` (4.4).

### 6.1 Hard constraints

| ID | Constraint | Error code |
|---|---|---|
| H01 | Shift inside [setup_start, clean_end] | INVALID_OPEN_SHIFT_START / INVALID_SHIFT_AFTER_CLEAN_END |
| H02 | ≤ 1 shift per employee per day | — |
| H03 | No overlap with any busy block of that weekday | EMPLOYEE_BUSY_CONFLICT |
| H04 | FT and manager shift = exactly 8 consecutive hours | INVALID_FT_SHIFT_LENGTH / INVALID_MANAGER_SHIFT_LENGTH |
| H05 | Regular PT shift = 4–8 whole hours | INVALID_PT_FRACTIONAL_SHIFT_LENGTH |
| H06 | Special PT (Training/NSO) = exactly 4h/day, ≤ 20h/week | INVALID_SPECIAL_LABOR_PT_SHIFT_LENGTH |
| H07 | FT/manager ≤ 48h/week | WEEKLY_HOUR_LIMIT |
| H08 | Store open 7 days → each fixed employee has exactly 1 OFF + 6 working days; **AL (8 paid h) only on the 6 working days, never on the OFF**. Store open < 7 days → work every open day, max 6 | INVALID_FT_WEEKLY_RULE |
| H09 | Each open day: openers ≥ open_staff, closers ≥ close_staff (MOD counts). Not applicable to 24h stores | INSUFFICIENT_OPENERS / INSUFFICIENT_CLOSERS |
| H10 | Each open day: 1 manager-group opener + 1 manager-group closer, 8h, locked. Not applicable to 24h stores | MANAGER_OPEN_GAP / MANAGER_CLOSE_GAP |
| H11 | ≥ 1 MOD in every operating slot (2+ allowed); extra manager shifts per 4.4 | INVALID_MANAGER_COVERAGE |
| H12 | Training-group manager works the exact same shift as a Regular manager | TRAINING_MANAGER_REGULAR_PAIR_REQUIRED |
| H13 | scheduled_staff ≥ 2 in every slot | MIN_STORE_COVERAGE_VIOLATION |
| H15 | Fixed employee with > 1 forced OFF in the week → error | FIXED_EMPLOYEE_MULTIPLE_FORCED_OFF_DAYS |
| H16 | Every shift (start, end) exists in `dim_shift_code` (enforced by 6.0) | REQUIRED_SHIFT_NO_CODE |
| H17 | 24h stores: after a shift that crosses midnight, no shift the next day starting before `MORNING_SHIFT_CUTOFF` (also across the week boundary) | MORNING_AFTER_NIGHT_SHIFT |

H14 (peak coverage hard rule) was removed with the return to band-first [DECISION 12-Nov-2026].

### 6.2 Soft constraints

| ID | Rule | Weight / note |
|---|---|---|
| S01 | Daily and weekly TCPH within [tcph, tcph × 1.05] | **Top objective (band-first)**: only H01–H13/H16 may override it; a coverage gap kept to stay in band is reported as `COVERAGE_SACRIFICED_FOR_TCPH_BAND` |
| S02 | Minimise staff_gap | 1,000 × gap² |
| S03 | Minimise overstaff | 25 |
| S04 | ≤ 1 manager-group OFF per day (unless forced) | MANAGER_GROUP_SAME_DAY_OFF_BREACH |
| S05 | OFF days on lowest-demand days, spread evenly; managers first | — |
| S06 | Manager pick order SM → ASM → SS, tie → fewer weekly hours; Barista Trainer fallback only | — |
| S07 | PT fairness: lowest-hour PT first (bonus for 0h PT); minimise variance of PT weekly hours | Zero-hour bonus 220, low-hour 28/h |
| S08 | Evening balance: split at middle slot; evening coverage ratio ≥ morning − 5 pts; evening gaps × 1.25 | 250 |
| S09 | Special PT reach 5 days / 20h | Filled last |
| S10 | Prefer using available staff over leaving them at 0h | 10 |
| S11 | Avoid PT shifts ≤ 4h | 2 |

### 6.3 Objective (minimise)

```python
# DEFAULT (TCPH_PRIORITY = "band_first")  [DECISION 12-Nov-2026] = demo
score = 1e8*tcph_out_of_band**2 + 1e6*manager_gap**2 + 1e4*close_gap \
      + 1e4*dist_to_band_center**2 + 1e3*staff_gap**2 + 1e3*overtime**2 \
      + 250*evening_gap + 25*overstaff + 25*daypart_imbalance \
      + 10*unused_available + 2*short_pt_shifts

# OPTION ONLY (TCPH_PRIORITY = "coverage_first") — not used by default
score = 1e8*manager_gap**2 + 1e7*peak_staff_gap**2 + 1e6*(open_gap + close_gap) \
      + 1e5*tcph_out_of_band**2 + 1e3*nonpeak_staff_gap**2 + 1e3*overtime**2 \
      + 250*evening_gap + 25*overstaff + 25*daypart_imbalance \
      + 10*unused_available + 2*short_pt_shifts + w_fair*pt_hours_variance
```

### 6.4 v0 — greedy pipeline (order matters, band-first = demo)

Before step 1: run the pre-flight (6.0).

1. Assign weekly OFF days (managers first, lowest-demand days, max 1 manager OFF/day; forced OFF from busy). AL days are placed on working days, never on the OFF.
2. Lock manager open + close shifts per day (H10); add MOD gap-fill shifts (4.4); pair Training managers (H12).
3. Place remaining FT 8h shifts on the best 8h window: score = manager_gap × 160 + labor_gap × 100 + peak × 20 − overstaff × 30.
4. Fill remaining open/close headcount with PT (4–8h anchored at setup_start / clean_end; side with larger gap first).
5. Fill coverage gaps with PT: new shifts for lowest-hour PT first, then extend existing PT shifts (evening weight 1.25).
6. Balance PT hours within the day (swap/shift without creating gaps).
7. Efficiency pass on non-locked PT only: shorten 1h → remove shift → move ±1h; accept if objective improves.
8. Daily KPI feedback loop (TCPH + coverage).
9. Weekly TCPH band check and roster completion.
10. Evening coverage repair (S08).
11. Weekly PT fairness swaps (S07).
12. Hard repair: ≥ 2 staff every slot (H13).
13. Fill special PT (Training/NSO) 4h shifts toward 5 days / 20h.
14. Run validation (Section 8).

Never modify locked manager shifts or FT shifts during steps 6–11. Steps 7–9 may cut PT hours to stay in the TCPH band, but never below H11 / H13.

### 6.5 v1 — CP-SAT formulation (target)

- **Shift templates:** from the pre-flight (6.0); per employee/day drop templates overlapping busy blocks.
- **Variables:** `x[e,d,t] ∈ {0,1}`, `off[e,d] ∈ {0,1}`, `al[e,d]` fixed from input.
- **Constraints:** H01–H13, H15–H17 linear (H17: `x[e,D,night] + x[e,D+1,morning] ≤ 1`); coverage per slot = Σ x over templates covering the slot (Section 4.3 mapping); MOD coverage = Σ over manager templates (+ Barista Trainer fallback via auxiliary var).
- **Objective:** Section 6.3 (band_first); gaps as non-negative slack variables.
- Time limit 30–60 s per store-week; return best feasible solution + gap report.

---

## 7. Outputs

### 7.1 Tables

| Table | Columns |
|---|---|
| `schedule` | employee_id, store_id, date, start, end, position, labor_group, is_paid_leave, tags (OPEN / CLOSE / LOCKED / AL) |
| `slot_coverage` | store_id, date, slot, forecast_tc, is_peak (forecast flag), labor_hours, required_staff, scheduled_staff, scheduled_manager, staff_gap, manager_gap, overstaff, status |
| `daily_kpi` | store_id, date, status (OPEN/CLOSED), day_type, adtc (Σ forecast_tc), labor_reg, labor_train, labor_nso, tcph, tcph_nso, forecast_run_id, method_version, publish_id, publish_version, published_at |
| `validation_issues` | store_id, week_start, code, severity (CRITICAL/WARNING/INFO), employee_id, date, slot, message |

### 7.2 File 2 — Attendance upload (Upload Phân Công)

Build from `schedule`, never from UI text.

- **File name:** `{StoreCode}_{ShortName}_Upload_Phan_Cong_{yyyymmdd}-{yyyymmdd}.xlsx` (Monday → Sunday). One sheet `Sheet1`.
- **Grain:** one row per employee × day, all 7 days (closed days as OFF).
- **Row order:** labor group (Regular → Training → NSO) → role (SM → ASM → SS → Barista Trainer → Crew) → within Crew FT before PT → name → employee_id.

| # | Header (exact text) | Value | Rule |
|---|---|---|---|
| A | Mã CH | `PL` followed by the last 4 digits of store code | Strip non-digits, keep last 4 (1023 → PL1023). No digits → store code as is |
| B | Mã nhân viên | employee_id | |
| C | Tên nhân viên | employee name | |
| D | Template | `2003` (number) | Constant on every row |
| E | Ngày bắt đầu (dd.MM.yyyy) | work date as text `dd.MM.yyyy` | week_start + day index |
| F | Ngày kết thúc (dd.MM.yyyy) | same as E | one row = one day |
| G | Mã ca làm việc/Loại nghỉ/ công tác (Tr.hợp phân loại nghỉ phép/ công tác thì phải phân ca của 2003 kèm theo, không phân ca OFF) | shift code / `OFF` | Rules below. Numeric-only codes as numbers, others as text |
| H | Giờ vào (HH:mm) | shift start | Excel time, format `HH:mm`; blank when OFF |
| I | Giờ ra (HH:mm) | shift end | Excel time, format `HH:mm`; blank when OFF |

**Column G (checked in order):**
1. Has a shift → code from `dim_shift_code` by exact (start, end); H/I = shift start/end.
2. No shift and AL (FT only) → code of 07:00–15:00 (`1180`); H/I = 07:00 / 15:00.
3. Otherwise (weekly OFF, busy OFF, PT not scheduled, closed day) → `OFF`; H/I blank.

**Blocking validation:** any shift (or the AL pair) without a matching code → do not write the file; return `employee_id - name - dd.MM.yyyy: HH:mm-HH:mm` (first 20 + count of the rest). Also block if week_start missing / not Monday, or no final roster.

Column widths (chars): 8, 14, 28, 10, 25, 25, 62, 16, 16.

### 7.3 Shift code lookup — `dim_shift_code`

- Source: `PLH_SHIFT_CODE_MAP` in the demo HTML (210 codes) → `PLH_Shift_Code_Map.csv`. Load as a reference table; master owner = HR.
- Match: exact `HH:mm` string on start and end; no rounding.
- Enforced **before** optimising by the pre-flight (6.0); the export check (7.2) stays as a safety net.
- For a 07:00–22:00 store all 105 possible shifts have a code (Appendix A). For other hours / 24h stores, the pre-flight decides which templates are usable.
- 12 pairs have 2 codes; demo takes the first in file order. Engine-reachable duplicates (HR to confirm): 08:00–16:00 `1114`/`11A8`, 10:00–18:00 `1168`/`1184`, 13:00–21:00 `1169`/`1189`. Until confirmed, use the first code.

---

## 8. Validation & KPI

### 8.1 KPI thresholds
- Utilization = demand labor ÷ scheduled labor: GOOD 0.90–1.05; ATTENTION 0.80–0.90 or 1.05–1.15; else FAIL.
- Coverage % and Manager coverage %: PASS ≥ 100%; RISK ≥ 95%; else FAIL.

### 8.2 Planning status
`HEALTHY` (Tốt) / `ATTENTION` (Cần chú ý) / `CRITICAL` (Rủi ro cao): CRITICAL if any FAIL or CRITICAL issue; ATTENTION if any ATTENTION / RISK / WARNING; else HEALTHY.

### 8.3 Recommendations (top 5 by impact)
Gap window ≥ 8h → +1 FT or +2 PT, else +⌈gap/4⌉ PT · overstaff ≥ 2h · PT max−min weekly hours ≥ 8h · ≥ 4 PT shifts ≤ 4h · ≥ 3 consecutive slots with zero buffer.

### 8.4 Planning window [DECISION 11-Nov-2026]
- week_start must be a Monday and **strictly later than the Monday of the current week** (no current or past weeks, including on Monday).
- Enforced on the server with server time in `Asia/Ho_Chi_Minh`; reject generate/publish requests that fail; log user + timestamp for every publish. UI check is a hint only.
- `ALLOW_PAST_WEEKS = True` (dev / back-test only) skips this check so past forecast weeks can be scheduled and compared with `actual_tc`; publish and File 2 export stay blocked in that mode.

---

## 9. Acceptance tests

- [ ] With tcph_target = 8 (test fixture): TC = 48 in slot → required_staff 6; TC = 12 → 2 (min rule); TC = 20 → 3 (2.5 rounds up).
- [ ] Store 2001, 2026-10-26, tcph_target = 8 (test fixture), hour 13, tc_p50 = 31.09 → labor_hours 3.89 → required_staff 4; hour 7, tc_p50 = 1.01 → 2 (min rule).
- [ ] Forecast loader picks only rows of the requested week_start and the latest `created_at`; hours 22–23 dropped for a 07:00–22:00 store (INFO with the dropped TC share, no warning).
- [ ] Missing operating hour in forecast → TC 0 + `FORECAST_MISSING_HOUR`; duplicate key → error.
- [ ] Slot requiring 3 is satisfied by 1 MOD + 2 staff; 3 staff without MOD → MANAGER_GAP.
- [ ] Slot mapping: 06:30–14:30 covers slots 07:00…14:00–15:00; 14:30–22:30 covers 14:00–15:00…21:00–22:00.
- [ ] FT with 1 AL day: 1 OFF + 5 worked + 1 AL = 48 paid hours; AL never on the OFF day.
- [ ] Band-first: when adding PT would push daily TCPH below tcph_target, the gap is left open and reported as `COVERAGE_SACRIFICED_FOR_TCPH_BAND` — unless the slot would fall below 2 staff or 0 MOD.
- [ ] Store 06:00–22:00 (window 05:30–22:30): open + close manager shifts leave a 1h gap → one extra manager-group shift fills it; a slot with 2 MODs is valid.
- [ ] 24h store: no setup/cleaning, H09/H10 skipped; a 22:00–06:00 shift on Monday covers Monday 22–24 and Tuesday 00–06.
- [ ] H17: employee on 22:00–06:00 Monday cannot get 06:00–14:00 Tuesday (→ `MORNING_AFTER_NIGHT_SHIFT`) but can get 14:00–22:00; employee on the previous week's Sunday night cannot get a Monday morning shift.
- [ ] Pre-flight drops templates without a code; a missing code for the FT open/close shift → `REQUIRED_SHIFT_NO_CODE`.
- [ ] Missing opening/closing time for a non-24h store → `STORE_HOURS_MISSING`.
- [ ] `ALLOW_PAST_WEEKS=True` lets W44–W46 run; publish/export stay blocked.
- [ ] Store without tcph_target → `TCPH_TARGET_MISSING`, no roster; target above max achievable → `TCPH_TARGET_INFEASIBLE` warning.
- [ ] No slot has < 2 staff or 0 MOD; every open day of a non-24h store has 2 openers and 2 closers incl. 1 manager each.
- [ ] Training manager shift start/end equals a Regular manager shift.
- [ ] Every shift in `schedule` maps to a code; an unmapped shift blocks File 2 with the error list.
- [ ] File 2 has employees × 7 rows; AL row = code 1180, 07:00–15:00; OFF rows have blank H/I.
- [ ] Server time Mon 2026-11-16 09:00 (Asia/Ho_Chi_Minh): week_start 2026-11-16 → rejected; 2026-11-23 → accepted; non-Monday → rejected; client clock has no effect.

---

## 10. Build plan

| Phase | Deliverable | Owner | Depends on | Done when |
|---|---|---|---|---|
| P0 Setup | Repo, config module, input loaders + validation (Section 2); real forecast, mock employees/busy for 1 store-week | Edward | — | Loaders pass validation tests |
| P1 Demand | `load_forecast()` (2.1, 5.1), `build_slot_demand()` (5.2), peak window, TCPH feasibility check, coverage evaluator (5.3) | Edward | `forecast_tc_hourly.parquet` (available) + `dim_store` hours + `tcph_target` per store (Thịnh) | Demand tests in Section 9 pass on 3 pilot stores |
| P2 Optimizer v0 | Pre-flight 6.0 + greedy pipeline 6.4 (band_first) | Edward | P1 | Hard constraints H01–H13, H15–H17 hold on the 3 pilot stores (incl. 1 store with ≠ 07–22 hours) + 1 24h store |
| P3 Validation & KPI | `validation_issues`, KPI, planning status, recommendations (Section 8) | Edward | P2 | All Section 9 tests pass |
| P4 Output | `schedule`, `slot_coverage`, `daily_kpi`, File 2 export (Section 7) | Edward | P2, `dim_shift_code` | File 2 opens and matches template; blocking rule works |
| P5 Pilot review | Run 2–3 pilot stores × 2 weeks; roster review | Thịnh | P4 + real data | Thịnh signs off feasibility |
| P6 Optimizer v1 | CP-SAT (6.5), compare vs v0 on pilot data | Edward | P5 | v1 ≥ v0 on coverage gap, TCPH, fairness |

**Suggested repo layout**

```
auto_scheduling/
  config.py              # constants (Section 3)
  io/loaders.py          # input contracts + validation (Section 2)
  io/forecast.py         # forecast_tc_hourly loader (2.1, 5.1)
  optimizer/preflight.py # 6.0
  demand/slots.py        # 4.3, 4.5, 5.1, 5.2
  demand/coverage.py     # 5.3
  optimizer/greedy.py    # 6.4 (v0)
  optimizer/cpsat.py     # 6.5 (v1)
  validation/rules.py    # 6.1, 8
  output/tables.py       # 7.1
  output/attendance.py   # 7.2, 7.3
  data/PLH_Shift_Code_Map.csv
  data/forecast_tc_hourly.parquet
tests/                   # Section 9
SPEC.md
```

---

## 11. Open questions

| # | Question | Owner | Blocks |
|---|---|---|---|
| Q1 | How should AL be uploaded? Demo sends it as a working shift 07:00–15:00 (code 1180), but column G says leave needs a leave type + 2003 shift | HR | P4 |
| Q2 | Meaning of Template = 2003; same for every store? | HR | P4 |
| Q3 | Weekly OFF and busy OFF both upload as `OFF` — is a separate code needed? | HR | P4 |
| Q4 | Correct code for 08:00–16:00, 10:00–18:00, 13:00–21:00 (duplicates) | HR | P4 |
| Q5 | PT no weekly cap and no min rest between shifts — legal check before go-live | HR/Legal | Go-live |
| Q6 | Is MOD 100% productive at peak, or partly supervising (count as 1.0 / 0.5 / separate)? | Thịnh | P5 |
| Q7 | Cup-based or hybrid demand driver (TC + cup)? Forecast has no cup column yet; check CPTC variation by hour | Giang / Thịnh | Post-v0 |
| Q8 | Setup / cleaning task lists (input for Step 2 workload model) | Thịnh | Step 2 |
| Q9 | Source of `dim_store` opening/closing time and is_24h flag (forecast suggests most stores start at 06:00 and 4 stores are 24h) | Thịnh / Tiền | **P1** |
| Q10 | OPS to provide `tcph_target` per store. Reference: with the 12-Nov forecast and 07:00–22:00, the 2-person floor alone caps daily TCPH at median 6.8 (P25 4.6, P75 9.4); a target of 8 is reachable on 37% of store-days. Targets above a store's cap will always breach the band | Thịnh | **P1** |
| Q11 | 24h stores: confirm overnight shifts (e.g. 22:00–06:00), that only coded shifts are used, and the "morning shift" cutoff for H17 (proposed: starts before 12:00). Is 14:00–22:00 the day after a night shift OK? | Thịnh / HR | P2 |
| Q12 | Band-first vs Thịnh's 05-Nov answer ("keep peak coverage"): align with Thịnh so pilot rosters are reviewed against the same rule | Edward / Thịnh | P5 |
| Q13 | Staff to tc_p50 or a higher quantile (e.g. p75 at peak hours) for a service buffer? | Edward / Thịnh | Post-v0 |
| Q14 | How is `is_peak` defined in the model (top-3 TC hours per store-day?) and is `forecast_tc_hourly` refreshed weekly on a fixed day? | Giang | P1 |

---

## Appendix A — Shift codes for a 07:00–22:00 store (105)

Full list (210 codes) in `PLH_Shift_Code_Map.csv`. Duplicates resolved to the first code in file order.

| Start | End | Hours | Code |
|---|---|---|---|
| 06:30 | 10:30 | 4 | 11E4 |
| 06:30 | 11:30 | 5 | 11Q9 |
| 06:30 | 12:30 | 6 | 11D8 |
| 06:30 | 13:30 | 7 | 11D9 |
| 06:30 | 14:30 | 8 | 1177 |
| 07:00 | 11:00 | 4 | 1126 |
| 07:00 | 12:00 | 5 | 1179 |
| 07:00 | 13:00 | 6 | 1152 |
| 07:00 | 14:00 | 7 | 1153 |
| 07:00 | 15:00 | 8 | 1180 |
| 07:30 | 11:30 | 4 | 11Q8 |
| 07:30 | 12:30 | 5 | 11R1 |
| 07:30 | 13:30 | 6 | 11R3 |
| 07:30 | 14:30 | 7 | 11R9 |
| 07:30 | 15:30 | 8 | 11B5 |
| 08:00 | 12:00 | 4 | 1127 |
| 08:00 | 13:00 | 5 | 1128 |
| 08:00 | 14:00 | 6 | 1154 |
| 08:00 | 15:00 | 7 | 1155 |
| 08:00 | 16:00 | 8 | 1114 |
| 08:30 | 12:30 | 4 | WD41 |
| 08:30 | 13:30 | 5 | 11T5 |
| 08:30 | 14:30 | 6 | 11S2 |
| 08:30 | 15:30 | 7 | 11T6 |
| 08:30 | 16:30 | 8 | 11B8 |
| 09:00 | 13:00 | 4 | 1129 |
| 09:00 | 14:00 | 5 | 1130 |
| 09:00 | 15:00 | 6 | 1156 |
| 09:00 | 16:00 | 7 | 1181 |
| 09:00 | 17:00 | 8 | 1182 |
| 09:30 | 13:30 | 4 | 11E5 |
| 09:30 | 14:30 | 5 | 11S4 |
| 09:30 | 15:30 | 6 | 11T7 |
| 09:30 | 16:30 | 7 | 11T8 |
| 09:30 | 17:30 | 8 | 11T9 |
| 10:00 | 14:00 | 4 | 1131 |
| 10:00 | 15:00 | 5 | 1132 |
| 10:00 | 16:00 | 6 | 1157 |
| 10:00 | 17:00 | 7 | 1183 |
| 10:00 | 18:00 | 8 | 1168 |
| 10:30 | 14:30 | 4 | 11S6 |
| 10:30 | 15:30 | 5 | 11U1 |
| 10:30 | 16:30 | 6 | 11U2 |
| 10:30 | 17:30 | 7 | 11U3 |
| 10:30 | 18:30 | 8 | 11B3 |
| 11:00 | 15:00 | 4 | 1133 |
| 11:00 | 16:00 | 5 | 1134 |
| 11:00 | 17:00 | 6 | 1158 |
| 11:00 | 18:00 | 7 | 1185 |
| 11:00 | 19:00 | 8 | 1186 |
| 11:30 | 15:30 | 4 | 11U4 |
| 11:30 | 16:30 | 5 | 11U5 |
| 11:30 | 17:30 | 6 | 11U6 |
| 11:30 | 18:30 | 7 | 11U7 |
| 11:30 | 19:30 | 8 | 11U8 |
| 12:00 | 16:00 | 4 | 1135 |
| 12:00 | 17:00 | 5 | 1136 |
| 12:00 | 18:00 | 6 | 1159 |
| 12:00 | 19:00 | 7 | 1187 |
| 12:00 | 20:00 | 8 | 1188 |
| 12:30 | 16:30 | 4 | 11U9 |
| 12:30 | 17:30 | 5 | 11V1 |
| 12:30 | 18:30 | 6 | 11R4 |
| 12:30 | 19:30 | 7 | 11V2 |
| 12:30 | 20:30 | 8 | 11B4 |
| 13:00 | 17:00 | 4 | 1137 |
| 13:00 | 18:00 | 5 | 1138 |
| 13:00 | 19:00 | 6 | 1160 |
| 13:00 | 20:00 | 7 | 11V3 |
| 13:00 | 21:00 | 8 | 1169 |
| 13:30 | 17:30 | 4 | 11E6 |
| 13:30 | 18:30 | 5 | 11R2 |
| 13:30 | 19:30 | 6 | 11V4 |
| 13:30 | 20:30 | 7 | 11V5 |
| 13:30 | 21:30 | 8 | 11B2 |
| 14:00 | 18:00 | 4 | 1139 |
| 14:00 | 19:00 | 5 | 1140 |
| 14:00 | 20:00 | 6 | 1161 |
| 14:00 | 21:00 | 7 | 1191 |
| 14:00 | 22:00 | 8 | 1192 |
| 14:30 | 18:30 | 4 | 11V6 |
| 14:30 | 19:30 | 5 | 11V7 |
| 14:30 | 20:30 | 6 | 11V8 |
| 14:30 | 21:30 | 7 | 11V9 |
| 14:30 | 22:30 | 8 | 1190 |
| 15:00 | 19:00 | 4 | 1141 |
| 15:00 | 20:00 | 5 | 1142 |
| 15:00 | 21:00 | 6 | 1162 |
| 15:00 | 22:00 | 7 | 1193 |
| 15:30 | 19:30 | 4 | 11W1 |
| 15:30 | 20:30 | 5 | 11W2 |
| 15:30 | 21:30 | 6 | 11W3 |
| 15:30 | 22:30 | 7 | 11S8 |
| 16:00 | 20:00 | 4 | 1143 |
| 16:00 | 21:00 | 5 | 1144 |
| 16:00 | 22:00 | 6 | 1163 |
| 16:30 | 20:30 | 4 | 11W4 |
| 16:30 | 21:30 | 5 | 11W5 |
| 16:30 | 22:30 | 6 | 11R5 |
| 17:00 | 21:00 | 4 | 1145 |
| 17:00 | 22:00 | 5 | 1146 |
| 17:30 | 21:30 | 4 | 11E7 |
| 17:30 | 22:30 | 5 | 1197 |
| 18:00 | 22:00 | 4 | 1148 |
| 18:30 | 22:30 | 4 | 11E1 |
