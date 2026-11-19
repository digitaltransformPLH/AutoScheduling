"""Login / logout / current user (accounts, roles and store assignments come from the .NET app)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import Connection

from .. import auth as a
from ..deps import get_conn
from ..schemas import LoginRequest, Me

router = APIRouter(prefix="/auth", tags=["auth"])

CAN = {"scheduleView": a.SCHEDULE_VIEW, "runEngine": a.RUN_ENGINE, "inputView": a.INPUT_VIEW, "employeeEdit": a.EMPLOYEE_EDIT,
       "availabilityEdit": a.AVAILABILITY_EDIT, "configEdit": a.CONFIG_EDIT, "hoursEdit": a.HOURS_EDIT}


def me_payload(user: a.User) -> dict:
    return {"user_id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role,
            "permissions": sorted(user.permissions), "all_stores": user.all_stores, "stores": sorted(user.stores),
            "can": {k: user.can(v) for k, v in CAN.items()}}


@router.post("/login", response_model=Me)
def login(req: LoginRequest, response: Response, conn: Connection = Depends(get_conn)) -> dict:
    user = a.check_password(conn, req.email, req.password)
    a.set_session_cookie(response, user.id)
    return me_payload(user)


@router.post("/logout", status_code=204)
def logout(response: Response) -> Response:
    a.clear_session_cookie(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=Me)
def me(user: a.User = Depends(a.current_user)) -> dict:
    return me_payload(user)
