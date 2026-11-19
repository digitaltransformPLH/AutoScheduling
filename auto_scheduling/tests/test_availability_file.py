"""Store Availability File workbook -> dim_employee + busy."""
import pandas as pd
import pytest

from auto_scheduling.inputs.availability_file import load_availability_file
from auto_scheduling.inputs.loaders import load_busy, load_employees
from auto_scheduling.issues import IssueLog
from auto_scheduling.timeutil import parse_hhmm


def _workbook(path):
    emp = pd.DataFrame([
        ["Nguyễn A", "6001", "Store Manager", "FT", "Regular", "Active"],
        ["Trần B", "6002", "Crew member", "PT", "Regular", "Active"],
        ["Lê C", "6003", "Crew member", "PT", "NSO", "Active"],
    ], columns=["Employee Name", "Employee ID", "Position", "Employment Type", "Labor group", "Status "])
    av = pd.DataFrame([
        ["Nguyễn A", "6001", "Store Manager", "FT", "Monday", None, None],
        ["Nguyễn A", "6001", "Store Manager", "FT", "Tuesday", "AL", "AL"],
        ["Trần B", "6002", "Crew member", "PT", "Monday", "15:00:00", "23:00:00"],
        ["Trần B", "6002", "Crew member", "PT", "Sunday", "07:00:00", "23:00:00"],
    ], columns=["Employee Name", "Employee ID", "Position", "Employment Type", "Ngày", "Bận từ", "Bận đến"])
    with pd.ExcelWriter(path) as xw:
        emp.to_excel(xw, sheet_name="Employee Master", index=False)
        av.to_excel(xw, sheet_name="Availability", index=False)
    return path


def test_parse_hhmm_with_seconds():
    assert parse_hhmm("15:00:00") == 900 and parse_hhmm("7:30") == 450


def test_busy_semantics(tmp_path):
    p = _workbook(tmp_path / "Availability File 9001.xlsx")
    emp, busy = load_availability_file(p, "9001")
    assert list(emp.columns) == ["employee_id", "store_id", "name", "position", "employment_type", "labor_group", "status"]
    assert emp["store_id"].eq("9001").all() and emp["employee_id"].tolist() == ["6001", "6002", "6003"]
    rows = busy.set_index(["employee_id", "weekday"])
    assert rows.loc[("6001", "Tuesday"), "busy_from"] == "AL"
    assert (rows.loc[("6002", "Monday"), "busy_from"], rows.loc[("6002", "Monday"), "busy_to"]) == ("15:00", "23:00")
    assert len(busy) == 3

    emp, busy = load_availability_file(p, "9001", busy_semantics="available")
    b = busy[busy["employee_id"] == "6002"].sort_values(["weekday", "busy_from"])
    mon = b[b["weekday"] == "Monday"][["busy_from", "busy_to"]].values.tolist()
    assert mon == [["00:00", "15:00"], ["23:00", "24:00"]]

    issues = IssueLog()
    emps = load_employees(emp, issues, store_id="9001")
    blocks = load_busy(busy, emps, issues, store_id="9001")
    assert not issues.has_critical() and len(blocks) == 5          # AL + 2x2 windows


def test_missing_sheet_columns(tmp_path):
    p = tmp_path / "bad.xlsx"
    pd.DataFrame({"x": [1]}).to_excel(p, sheet_name="Employee Master", index=False)
    with pytest.raises(ValueError):
        load_availability_file(p, "1")
