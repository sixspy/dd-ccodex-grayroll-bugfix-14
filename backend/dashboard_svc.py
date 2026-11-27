"""控制台摘要。"""
from __future__ import annotations

from fastapi import APIRouter, Header

from auth import current_user
from db import connect
from models import FLAG_STATUS_LABEL

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(authorization: str | None = Header(default=None)):
    current_user(authorization)
    with connect() as conn:
        flags = conn.execute("SELECT COUNT(*) c FROM flags").fetchone()["c"]
        # 灰态归档开关不得计入已生效（gbf14：原口径把 archived 算入导致虚高假绿）。
        active = conn.execute(
            "SELECT COUNT(*) c FROM flags WHERE status='active'"
        ).fetchone()["c"]
        killed = conn.execute("SELECT COUNT(*) c FROM flags WHERE status='killed'").fetchone()["c"]
        releases = conn.execute("SELECT COUNT(*) c FROM releases WHERE official=1").fetchone()["c"]
        shadows = conn.execute(
            "SELECT COUNT(*) c FROM release_shadows WHERE status='open'"
        ).fetchone()["c"]
        overrides = conn.execute("SELECT COUNT(*) c FROM overrides WHERE active=1").fetchone()["c"]
        # 可放量计数与正式名册同源：直接数 rollout_roster（其刷新已同事务剔除灰态）。
        releasable = conn.execute("SELECT COUNT(*) c FROM rollout_roster").fetchone()["c"]
        by_status = [
            {
                "status": r["status"],
                "label": FLAG_STATUS_LABEL.get(r["status"], r["status"]),
                "c": r["c"],
            }
            for r in conn.execute("SELECT status, COUNT(*) c FROM flags GROUP BY status").fetchall()
        ]
        recent = [
            dict(r)
            for r in conn.execute(
                "SELECT id, action, detail, actor, created_at FROM change_history ORDER BY id DESC LIMIT 8"
            ).fetchall()
        ]
    return {
        "flags": flags,
        "active": active,
        "killed": killed,
        "releases": releases,
        "open_shadows": shadows,
        "active_overrides": overrides,
        "releasable_count": releasable,
        "by_status": by_status,
        "recent": recent,
    }
