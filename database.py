# database.py
import sqlite3
import json
import time
import os
from datetime import datetime
from threading import Lock

DB_PATH = os.environ.get("DB_PATH", "bot.db")
_lock = Lock()

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    with _lock:
        conn = get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY,
                username    TEXT,
                name        TEXT,
                lang        TEXT DEFAULT 'ru'
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id     INTEGER PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS premium (
                user_id     INTEGER PRIMARY KEY,
                expire      INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS premium_plus (
                user_id     INTEGER PRIMARY KEY,
                expire      INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS global_tests (
                test_id     TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                questions   TEXT NOT NULL,
                split       INTEGER DEFAULT 30,
                time        INTEGER DEFAULT 60,
                order_type  TEXT DEFAULT 'normal',
                owner_id    INTEGER
            );

            CREATE TABLE IF NOT EXISTS user_tests (
                user_id     INTEGER NOT NULL,
                test_id     TEXT NOT NULL,
                PRIMARY KEY (user_id, test_id)
            );

            CREATE TABLE IF NOT EXISTS ready_tests (
                test_id     TEXT PRIMARY KEY,
                added_by    INTEGER,
                added_date  TEXT
            );

            CREATE TABLE IF NOT EXISTS admin_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id    INTEGER,
                admin_name  TEXT,
                action      TEXT,
                target_user TEXT,
                details     TEXT,
                timestamp   TEXT
            );

            CREATE TABLE IF NOT EXISTS test_results (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id     TEXT,
                group_key   TEXT,
                user_id     INTEGER,
                username    TEXT,
                score       INTEGER,
                total       INTEGER,
                time_spent  REAL,
                date        TEXT
            );
        """)
        conn.commit()
        conn.close()

# ── USERS ──────────────────────────────────────────────────────────────────

def db_save_user(user):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO users (id, username, name, lang) VALUES (?, ?, ?, 'ru')",
            (user.id, user.username, user.full_name)
        )
        conn.commit()
        conn.close()

def db_load_users() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return {str(r["id"]): dict(r) for r in rows}

def db_get_user_lang(user_id: int) -> str:
    conn = get_conn()
    row = conn.execute("SELECT lang FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return row["lang"] if row else "ru"

def db_set_user_lang(user_id: int, lang: str):
    with _lock:
        conn = get_conn()
        conn.execute("UPDATE users SET lang=? WHERE id=?", (lang, user_id))
        conn.commit()
        conn.close()

def db_find_user(query: str):
    query = str(query).lower()
    conn = get_conn()
    rows = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    for row in rows:
        d = dict(row)
        if (query in (d.get("username") or "").lower() or
            query in (d.get("name") or "").lower() or
            query in str(d["id"])):
            return str(d["id"]), d
    return None, None

# ── ADMINS ─────────────────────────────────────────────────────────────────

def db_load_admins() -> list:
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM admins").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]

def db_add_admin(user_id: int):
    with _lock:
        conn = get_conn()
        conn.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
        conn.commit()
        conn.close()

def db_remove_admin(user_id: int):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()

# ── PREMIUM ────────────────────────────────────────────────────────────────

def db_add_premium(user_id, days: int):
    expire = int(time.time()) + days * 86400
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO premium (user_id, expire) VALUES (?, ?)",
            (user_id, expire)
        )
        conn.commit()
        conn.close()

def db_remove_premium(user_id):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM premium WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()

def db_is_premium(user_id) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT expire FROM premium WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return False
    if time.time() > row["expire"]:
        db_remove_premium(user_id)
        return False
    return True

def db_get_premium_time_left(user_id) -> str | None:
    conn = get_conn()
    row = conn.execute("SELECT expire FROM premium WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return None
    left = row["expire"] - time.time()
    if left <= 0:
        return None
    return f"{int(left // 86400)} дн. {int((left % 86400) // 3600)} ч."

def db_load_premium_users() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT user_id, expire FROM premium").fetchall()
    conn.close()
    return {str(r["user_id"]): r["expire"] for r in rows}

def db_clear_premium():
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM premium")
        conn.commit()
        conn.close()

# ── PREMIUM+ ────────────────────────────────────────────────────────────────

def db_add_premium_plus(user_id, days: int):
    expire = int(time.time()) + days * 86400
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO premium_plus (user_id, expire) VALUES (?, ?)",
            (user_id, expire)
        )
        conn.commit()
        conn.close()

def db_remove_premium_plus(user_id):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM premium_plus WHERE user_id=?", (user_id,))
        conn.commit()
        conn.close()

def db_is_premium_plus(user_id) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT expire FROM premium_plus WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return False
    if time.time() > row["expire"]:
        db_remove_premium_plus(user_id)
        return False
    return True

def db_clear_premium_plus():
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM premium_plus")
        conn.commit()
        conn.close()

def db_load_premium_plus_users() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT user_id, expire FROM premium_plus").fetchall()
    conn.close()
    return {str(r["user_id"]): r["expire"] for r in rows}

# ── GLOBAL TESTS ───────────────────────────────────────────────────────────

import random as _random

def db_save_global_test(test_data: dict, owner_id: int = None) -> str:
    conn = get_conn()
    existing = {r["test_id"] for r in conn.execute("SELECT test_id FROM global_tests").fetchall()}
    conn.close()
    test_id = str(_random.randint(1000000, 9999999))
    while test_id in existing:
        test_id = str(_random.randint(1000000, 9999999))
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO global_tests (test_id, name, questions, split, time, order_type, owner_id) VALUES (?,?,?,?,?,?,?)",
            (
                test_id,
                test_data["name"],
                json.dumps(test_data["questions"], ensure_ascii=False),
                test_data.get("split", 30),
                test_data.get("time", 60),
                test_data.get("order", "normal"),
                owner_id,
            )
        )
        conn.commit()
        conn.close()
    return test_id

def db_load_global_test(test_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM global_tests WHERE test_id=?", (test_id,)).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["questions"] = json.loads(d["questions"])
    d["order"] = d.pop("order_type", "normal")
    return d

def db_load_global_tests() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM global_tests").fetchall()
    conn.close()
    result = {}
    for row in rows:
        d = dict(row)
        d["questions"] = json.loads(d["questions"])
        d["order"] = d.pop("order_type", "normal")
        result[d["test_id"]] = d
    return result

def db_delete_global_test(test_id: str):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM global_tests WHERE test_id=?", (test_id,))
        conn.commit()
        conn.close()

def db_update_test_field(test_id: str, field: str, value):
    allowed = {"name", "time", "order_type", "split"}
    if field not in allowed:
        return
    with _lock:
        conn = get_conn()
        conn.execute(f"UPDATE global_tests SET {field}=? WHERE test_id=?", (value, test_id))
        conn.commit()
        conn.close()

# ── USER TESTS ─────────────────────────────────────────────────────────────

def db_save_user_test_id(user_id, test_id: str):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT OR IGNORE INTO user_tests (user_id, test_id) VALUES (?, ?)",
            (user_id, test_id)
        )
        conn.commit()
        conn.close()

def db_load_user_test_ids(user_id) -> list:
    conn = get_conn()
    rows = conn.execute("SELECT test_id FROM user_tests WHERE user_id=?", (user_id,)).fetchall()
    conn.close()
    return [r["test_id"] for r in rows]

def db_delete_user_test_id(user_id, test_id: str):
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM user_tests WHERE user_id=? AND test_id=?", (user_id, test_id))
        conn.commit()
        conn.close()

# ── READY TESTS ────────────────────────────────────────────────────────────

def db_load_ready_tests() -> dict:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM ready_tests").fetchall()
    conn.close()
    return {r["test_id"]: dict(r) for r in rows}

def db_add_to_ready_tests(test_id: str, admin_id: int) -> bool:
    conn = get_conn()
    exists = conn.execute("SELECT 1 FROM ready_tests WHERE test_id=?", (test_id,)).fetchone()
    conn.close()
    if exists:
        return False
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO ready_tests (test_id, added_by, added_date) VALUES (?, ?, ?)",
            (test_id, admin_id, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()
    return True

def db_remove_from_ready_tests(test_id: str) -> bool:
    conn = get_conn()
    exists = conn.execute("SELECT 1 FROM ready_tests WHERE test_id=?", (test_id,)).fetchone()
    conn.close()
    if not exists:
        return False
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM ready_tests WHERE test_id=?", (test_id,))
        conn.commit()
        conn.close()
    return True

# ── ADMIN LOGS ─────────────────────────────────────────────────────────────

def db_log_admin_action(admin_id: int, admin_name: str, action: str, target_user, details: str):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO admin_logs (admin_id, admin_name, action, target_user, details, timestamp) VALUES (?,?,?,?,?,?)",
            (admin_id, admin_name, action, str(target_user), details, datetime.now().isoformat())
        )
        conn.execute("""
            DELETE FROM admin_logs WHERE id NOT IN (
                SELECT id FROM admin_logs ORDER BY id DESC LIMIT 500
            )
        """)
        conn.commit()
        conn.close()

def db_get_admin_logs(limit=50) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM admin_logs ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def db_clear_admin_logs():
    with _lock:
        conn = get_conn()
        conn.execute("DELETE FROM admin_logs")
        conn.commit()
        conn.close()

# ── TEST RESULTS ───────────────────────────────────────────────────────────

def db_save_test_result(test_id, group_key, user_id, username, score, total, time_spent):
    with _lock:
        conn = get_conn()
        conn.execute(
            "INSERT INTO test_results (test_id, group_key, user_id, username, score, total, time_spent, date) VALUES (?,?,?,?,?,?,?,?)",
            (test_id, group_key, user_id, username, score, total, round(time_spent, 1), datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

def db_get_leaderboard(test_id, group_key, limit=10) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM test_results WHERE test_id=? AND group_key=? ORDER BY score DESC, time_spent ASC LIMIT ?",
        (test_id, group_key, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]