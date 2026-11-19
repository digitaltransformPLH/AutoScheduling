"""API tests. Unit: OpenAPI, helpers, password hash, session cookie (no DB). Integration (`pytest -m integration`): real SQL Server.

Integration tests log in through a dependency override (fake users) and never write: edits are checked in preview mode
(Excel) or inside a rolled-back transaction.
"""
import time
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sched_api import auth as a
from sched_api.deps import clean, snake
from sched_api.main import API_PREFIX, app

client = TestClient(app)
ALL = frozenset(v for k, v in vars(a.P).items() if k.isupper())
ADMIN = a.User(1, "admin@test", "Admin", "Administrator", ALL, True, frozenset())
MANAGER = a.User(2, "mgr@test", "Mgr", "Manager", frozenset({a.P.PLANNING_INPUT_VIEW, a.P.PLANNING_OVERVIEW_VIEW, a.P.AVAILABILITY_MANAGE,
                                                           a.P.STORE_CONFIG_MANAGE}), False, frozenset({"2189"}))


@pytest.fixture
def as_user():
    def login(user):
        app.dependency_overrides[a.current_user] = lambda: user
    yield login
    app.dependency_overrides.clear()


def test_snake_and_clean():
    from datetime import time as t
    from decimal import Decimal
    assert [snake(x) for x in ("WeekStart", "ADTC", "TcphInclNso", "Is24h", "StoreCode")] == \
        ["week_start", "adtc", "tcph_incl_nso", "is24h", "store_code"]
    assert clean(Decimal("5.75")) == 5.75 and clean(t(6, 30)) == "06:30" and clean(date(2026, 11, 9)) == "2026-11-09"


def test_openapi_paths():
    paths = app.openapi()["paths"]
    for p in ("/meta", "/stores", "/schedules/{store}/{week}/overview", "/schedules/{store}/{week}/file2", "/runs", "/runs/{run_id}",
              "/auth/login", "/auth/logout", "/auth/me", "/inputs/options", "/inputs/employees", "/inputs/employees/{employee_id}",
              "/inputs/availability", "/inputs/availability/{store}/{week}", "/inputs/availability/{store}/{week}/copy",
              "/inputs/secondments", "/inputs/secondments/{sec_id}", "/inputs/store-config", "/inputs/store-config/{store}",
              "/inputs/excel/availability-file", "/inputs/excel/secondments", "/inputs/excel/store-config", "/inputs/shift-codes"):
        assert API_PREFIX + p in paths, p
    schemas = app.openapi()["components"]["schemas"]
    assert "weekStart" in schemas["ScheduleWeek"]["properties"]                 # camelCase JSON


def test_aspnet_password_hash():
    # test vectors of ASP.NET Core Identity PasswordHasher (v3 = PBKDF2-SHA256 10k, v2 = PBKDF2-SHA1 1k)
    v3 = "AQAAAAEAACcQAAAAEAABAgMEBQYHCAkKCwwNDg+yWU7rLgUwPZb1Itsmra7cbxw2EFpwpVFIEtP+JIuUEw=="
    v2 = "AAABAgMEBQYHCAkKCwwNDg+ukCEMDf0yyQ29NYubggHIVY0sdEUfdyeM+E1LtH1uJg=="
    assert a.verify_aspnet_hash(v3, "my password") and a.verify_aspnet_hash(v2, "my password")
    assert not a.verify_aspnet_hash(v3, "My password") and not a.verify_aspnet_hash(v2, "")
    assert not a.verify_aspnet_hash("not base64 !!", "x") and not a.verify_aspnet_hash(None, "x") and not a.verify_aspnet_hash("AQ==", "x")


def test_session_cookie():
    tok = a.sign_session(42)
    assert a.read_session(tok)["uid"] == 42
    body, sig = tok.split(".")
    assert a.read_session(body + "." + sig[:-2] + "AA") is None                   # tampered signature
    assert a.read_session(tok, now=time.time() + 11 * 3600) is None               # expired (10 h)
    assert a.read_session(None) is None and a.read_session("x.y.z") is None


def test_user_scope():
    assert MANAGER.can_store("2189") and not MANAGER.can_store("2184") and ADMIN.can_store("2184")
    assert MANAGER.can(a.AVAILABILITY_EDIT) and not MANAGER.can(a.EMPLOYEE_EDIT) and not MANAGER.can(a.HOURS_EDIT)


def test_week_validation(as_user):
    as_user(ADMIN)
    assert client.get(f"{API_PREFIX}/schedules/2184/2026-11-10/overview").status_code == 422   # not a Monday


@pytest.mark.integration
def test_requires_login():
    assert client.get(f"{API_PREFIX}/stores").status_code == 401
    assert client.get(f"{API_PREFIX}/auth/me").status_code == 401
    assert client.post(f"{API_PREFIX}/auth/login", json={"email": "nobody@example.invalid", "password": "x"}).status_code == 401


@pytest.mark.integration
def test_overview_pilot_store(as_user):
    as_user(ADMIN)
    r = client.get(f"{API_PREFIX}/schedules/2184/2026-11-09/overview")
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["week"]["storeCode"] == "2184" and len(d["days"]) == 7 and len(d["hourly"]) == 105 and len(d["roster"]) == 147
    assert {x["dayType"] for x in d["roster"]} >= {"Làm", "OFF", "Đi hỗ trợ"}
    assert r.json()["meta"]["dataVersion"] > 0


@pytest.mark.integration
def test_stores_inputs_file2(as_user):
    as_user(ADMIN)
    stores = client.get(f"{API_PREFIX}/stores", params={"ready_only": True}).json()["data"]
    assert {"2189", "2184", "2030"} <= {s["storeCode"] for s in stores}
    assert len([e for e in client.get(f"{API_PREFIX}/inputs/employees", params={"store": "2189"}).json()["data"] if e["status"] == "Active"]) == 15
    f = client.get(f"{API_PREFIX}/schedules/2189/2026-11-09/file2")
    assert f.status_code == 200 and f.content[:2] == b"PK" and "Upload_Phan_Cong_20261109-20261115" in f.headers["content-disposition"]
    assert client.get(f"{API_PREFIX}/schedules/2189/2020-01-06/overview").status_code == 404


@pytest.mark.integration
def test_store_scope_and_permissions(as_user):
    as_user(MANAGER)
    assert [s["storeCode"] for s in client.get(f"{API_PREFIX}/stores").json()["data"]] == ["2189"]
    assert client.get(f"{API_PREFIX}/schedules/2184/2026-11-09/overview").status_code == 403
    assert client.get(f"{API_PREFIX}/inputs/employees", params={"store": "2184"}).status_code == 403
    assert client.post(f"{API_PREFIX}/runs", json={"storeCode": "2189", "weekStart": "2026-11-09"}).status_code == 403
    assert client.post(f"{API_PREFIX}/inputs/employees", json={"storeCode": "2189", "employeeId": "1", "employeeName": "x",
                                                              "position": "Crew member", "employmentType": "PT", "laborGroup": "Regular"}).status_code == 403


@pytest.mark.integration
@pytest.mark.parametrize("store", ["2189", "2184", "2030"])
def test_excel_roundtrip_has_no_changes(as_user, store):
    """Download the current data and upload it again (preview): nothing to change, no errors."""
    as_user(ADMIN)
    x = client.get(f"{API_PREFIX}/inputs/excel/availability-file", params={"store": store, "week": "2026-11-16"})
    assert x.status_code == 200 and x.content[:2] == b"PK"
    r = client.post(f"{API_PREFIX}/inputs/excel/availability-file", files={"file": ("a.xlsx", x.content)},
                    data={"store": store, "week": "2026-11-16", "replace_employees": "true", "replace_busy": "true"}).json()
    assert r["canApply"] and not r["applied"] and not r["errors"]
    assert [c["action"] for c in r["changes"]] == ["Thay lịch bận"]                # employees unchanged, busy rows rewritten 1:1
    s = client.get(f"{API_PREFIX}/inputs/excel/secondments", params={"store": store})
    r = client.post(f"{API_PREFIX}/inputs/excel/secondments", data={"store": store}, files={"file": ("s.xlsx", s.content)}).json()
    assert r["canApply"] and not r["errors"]


@pytest.mark.integration
def test_edits_in_rolled_back_transaction():
    from auto_scheduling.db import get_engine
    from fastapi import HTTPException
    from sched_api import input_edit as ed
    from sqlalchemy import text
    with get_engine().connect() as conn:
        tx = conn.begin()
        try:
            ed.create_employee(conn, "2189", "99999001", "Test", "Crew member", "PT", "Regular", "Active", "t@test")
            with pytest.raises(HTTPException) as e:
                ed.create_employee(conn, "2189", "99999001", "Dup", "Crew member", "PT", "Regular", "Active", "t@test")
            assert e.value.status_code == 409
            ed.upsert_availability_day(conn, "2189", date(2026, 11, 16), "99999001", date(2026, 11, 18), "07:00", "12:00", False)
            with pytest.raises(HTTPException):
                ed.upsert_availability_day(conn, "2189", date(2026, 11, 16), "99999001", date(2026, 11, 19), "12:00", "07:00", False)
            ed.create_secondment(conn, "99999001", "2189", "2030", date(2026, 11, 20), date(2026, 11, 21), "t@test")
            with pytest.raises(HTTPException):                                     # overlapping loan
                ed.create_secondment(conn, "99999001", "2189", "2184", date(2026, 11, 21), date(2026, 11, 22), "t@test")
            busy = conn.execute(text("SELECT CONVERT(CHAR(5), BusyFrom, 108) FROM dbo.employee_availability_slot WHERE EmployeeNumber = 99999001")).scalar()
            assert busy == "07:00"
        finally:
            tx.rollback()


@pytest.mark.integration
def test_shift_codes_endpoint(as_user):
    as_user(ADMIN)
    data = client.get(f"{API_PREFIX}/inputs/shift-codes").json()["data"]
    assert len(data) == 210 and {"11E1", "1180"} <= {d["shiftCode"] for d in data}
    night = next(d for d in data if d["shiftCode"] == "11P9")
    assert (night["startTime"], night["endTime"], night["isOvernight"]) == ("18:00", "02:00", True)
