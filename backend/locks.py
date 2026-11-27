"""行锁与争用痕（嵌进发布/熔断主写路径）。"""
from __future__ import annotations

import time

from fastapi import APIRouter, Header, HTTPException

from auth import current_user
from db import connect

router = APIRouter(prefix="/api/locks", tags=["locks"])
TTL = 20.0


def acquire(conn, key: str, holder: str) -> None:
    """原子获取持久行锁。

    用 BEGIN IMMEDIATE 把「检查 + 占位」串行化为一个短写事务：
      - 已有未过期且持有者非本人的行锁 -> 判败，回滚后在独立短事务写
        contention_marks 争用痕并抛 409，败方不进入业务取舍段、零正式改；
      - 否则 upsert 占位并立即提交，行锁持久驻留（对其他连接立即可见），
        DB 写锁随即释放；临界区互斥改由这把持久行锁表达，直到 release 删除。
    后来者在胜方业务段内到达时，能读到驻留行锁而稳定判败。
    """
    now = time.time()
    conn.execute("BEGIN IMMEDIATE")
    row = conn.execute("SELECT * FROM row_locks WHERE lock_key=?", (key,)).fetchone()
    if row and row["expires_at"] > now and row["holder"] != holder:
        conn.rollback()
        conn.execute(
            "INSERT INTO contention_marks(lock_key, loser, winner, created_at) VALUES(?,?,?,?)",
            (key, holder, row["holder"], now),
        )
        conn.commit()
        raise HTTPException(409, detail="发布锁争用，请稍后重试")
    conn.execute(
        "INSERT INTO row_locks(lock_key, holder, expires_at) VALUES(?,?,?) "
        "ON CONFLICT(lock_key) DO UPDATE SET holder=excluded.holder, expires_at=excluded.expires_at",
        (key, holder, now + TTL),
    )
    # 提交即释放 DB 写锁，但行锁行持久驻留，供后来者读取判败。
    conn.commit()


def release(conn, key: str, holder: str) -> None:
    """删除持久行锁并提交，结束临界区。"""
    conn.execute("DELETE FROM row_locks WHERE lock_key=? AND holder=?", (key, holder))
    conn.commit()


@router.get("/contention")
def list_contention(authorization: str | None = Header(default=None), limit: int = 40):
    current_user(authorization)
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM contention_marks ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return {"items": [dict(r) for r in rows]}
