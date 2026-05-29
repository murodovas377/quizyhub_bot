# database.py  —  PostgreSQL версия (Railway)
import json
import time
import os
import random as _random
from datetime import datetime
from threading import Lock

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL", "")
_lock = Lock()


def get_conn():
    conn = psycopg2.connect(DATABASE_URL)
    return conn


def init_db():
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          BIGINT PRIMARY KEY,
                username    TEXT,
                name        TEXT,
                lang        TEXT DEFAULT 'ru'
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id     BIGINT PRIMARY KEY
            );

            CREATE TABLE IF NOT EXISTS premium (
                user_id     BIGINT PRIMARY KEY,
                expire      BIGINT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS premium_plus (
                user_id     BIGINT PRIMARY KEY,
                expire      BIGINT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS global_tests (
                test_id     TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                questions   TEXT NOT NULL,
                split       INTEGER DEFAULT 30,
                time        INTEGER DEFAULT 60,
                order_type  TEXT DEFAULT 'normal',
                owner_id    BIGINT
            );

            CREATE TABLE IF NOT EXISTS user_tests (
                user_id     BIGINT NOT NULL,
                test_id     TEXT NOT NULL,
                PRIMARY KEY (user_id, test_id)
            );

            CREATE TABLE IF NOT EXISTS ready_tests (
                test_id     TEXT PRIMARY KEY,
                added_by    BIGINT,
                added_date  TEXT
            );

            CREATE TABLE IF NOT EXISTS admin_logs (
                id          SERIAL PRIMARY KEY,
                admin_id    BIGINT,
                admin_name  TEXT,
                action      TEXT,
                target_user TEXT,
                details     TEXT,
                timestamp   TEXT
            );

            CREATE TABLE IF NOT EXISTS test_results (
                id          SERIAL PRIMARY KEY,
                test_id     TEXT,
                group_key   TEXT,
                user_id     BIGINT,
                username    TEXT,
                score       INTEGER,
                total       INTEGER,
                time_spent  REAL,
                date        TEXT
            );
        """)
        conn.commit()
        cur.close()
        conn.close()


def _row_to_dict(cur, row):
    """Конвертировать строку в dict по именам колонок"""
    cols = [desc[0] for desc in cur.description]
    return dict(zip(cols, row))


# ── USERS ──────────────────────────────────────────────────────────────────

def db_save_user(user):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (id, username, name, lang) VALUES (%s, %s, %s, 'ru') ON CONFLICT (id) DO NOTHING",
            (user.id, user.username, user.full_name)
        )
        conn.commit()
        cur.close()
        conn.close()


def db_load_users() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    result = {str(r[0]): _row_to_dict(cur, r) for r in rows}
    cur.close()
    conn.close()
    return result


def db_get_user_lang(user_id: int) -> str:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else "ru"


def db_set_user_lang(user_id: int, lang: str):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("UPDATE users SET lang=%s WHERE id=%s", (lang, user_id))
        conn.commit()
        cur.close()
        conn.close()


def db_find_user(query: str):
    query = str(query).lower()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    rows = cur.fetchall()
    for row in rows:
        d = _row_to_dict(cur, row)
        if (query in (d.get("username") or "").lower() or
            query in (d.get("name") or "").lower() or
            query in str(d["id"])):
            cur.close()
            conn.close()
            return str(d["id"]), d
    cur.close()
    conn.close()
    return None, None


# ── ADMINS ─────────────────────────────────────────────────────────────────

def db_load_admins() -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM admins")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]


def db_add_admin(user_id: int):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO admins (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
        conn.commit()
        cur.close()
        conn.close()


def db_remove_admin(user_id: int):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM admins WHERE user_id=%s", (user_id,))
        conn.commit()
        cur.close()
        conn.close()


# ── PREMIUM ────────────────────────────────────────────────────────────────

def db_add_premium(user_id, days: int):
    expire = int(time.time()) + days * 86400
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO premium (user_id, expire) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET expire=EXCLUDED.expire",
            (user_id, expire)
        )
        conn.commit()
        cur.close()
        conn.close()


def db_remove_premium(user_id):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM premium WHERE user_id=%s", (user_id,))
        conn.commit()
        cur.close()
        conn.close()


def db_is_premium(user_id) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT expire FROM premium WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return False
    if time.time() > row[0]:
        db_remove_premium(user_id)
        return False
    return True


def db_get_premium_time_left(user_id) -> str | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT expire FROM premium WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return None
    left = row[0] - time.time()
    if left <= 0:
        return None
    return f"{int(left // 86400)} дн. {int((left % 86400) // 3600)} ч."


def db_load_premium_users() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, expire FROM premium")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {str(r[0]): r[1] for r in rows}


def db_clear_premium():
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM premium")
        conn.commit()
        cur.close()
        conn.close()


# ── PREMIUM+ ────────────────────────────────────────────────────────────────

def db_add_premium_plus(user_id, days: int):
    expire = int(time.time()) + days * 86400
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO premium_plus (user_id, expire) VALUES (%s, %s) ON CONFLICT (user_id) DO UPDATE SET expire=EXCLUDED.expire",
            (user_id, expire)
        )
        conn.commit()
        cur.close()
        conn.close()


def db_remove_premium_plus(user_id):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM premium_plus WHERE user_id=%s", (user_id,))
        conn.commit()
        cur.close()
        conn.close()


def db_is_premium_plus(user_id) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT expire FROM premium_plus WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if not row:
        return False
    if time.time() > row[0]:
        db_remove_premium_plus(user_id)
        return False
    return True


def db_clear_premium_plus():
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM premium_plus")
        conn.commit()
        cur.close()
        conn.close()


def db_load_premium_plus_users() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT user_id, expire FROM premium_plus")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {str(r[0]): r[1] for r in rows}


# ── GLOBAL TESTS ───────────────────────────────────────────────────────────

def db_save_global_test(test_data: dict, owner_id: int = None) -> str:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT test_id FROM global_tests")
    existing = {r[0] for r in cur.fetchall()}
    cur.close()
    conn.close()

    test_id = str(_random.randint(1000000, 9999999))
    while test_id in existing:
        test_id = str(_random.randint(1000000, 9999999))

    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO global_tests (test_id, name, questions, split, time, order_type, owner_id) VALUES (%s,%s,%s,%s,%s,%s,%s)",
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
        cur.close()
        conn.close()
    return test_id


def db_load_global_test(test_id: str) -> dict | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM global_tests WHERE test_id=%s", (test_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return None
    d = _row_to_dict(cur, row)
    cur.close()
    conn.close()
    d["questions"] = json.loads(d["questions"])
    d["order"] = d.pop("order_type", "normal")
    return d


def db_load_global_tests() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM global_tests")
    rows = cur.fetchall()
    result = {}
    for row in rows:
        d = _row_to_dict(cur, row)
        d["questions"] = json.loads(d["questions"])
        d["order"] = d.pop("order_type", "normal")
        result[d["test_id"]] = d
    cur.close()
    conn.close()
    return result


def db_delete_global_test(test_id: str):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM global_tests WHERE test_id=%s", (test_id,))
        conn.commit()
        cur.close()
        conn.close()


def db_update_test_field(test_id: str, field: str, value):
    allowed = {"name", "time", "order_type", "split"}
    if field not in allowed:
        return
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(f"UPDATE global_tests SET {field}=%s WHERE test_id=%s", (value, test_id))
        conn.commit()
        cur.close()
        conn.close()


# ── USER TESTS ─────────────────────────────────────────────────────────────

def db_save_user_test_id(user_id, test_id: str):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO user_tests (user_id, test_id) VALUES (%s, %s) ON CONFLICT (user_id, test_id) DO NOTHING",
            (user_id, test_id)
        )
        conn.commit()
        cur.close()
        conn.close()


def db_load_user_test_ids(user_id) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT test_id FROM user_tests WHERE user_id=%s", (user_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]


def db_delete_user_test_id(user_id, test_id: str):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM user_tests WHERE user_id=%s AND test_id=%s", (user_id, test_id))
        conn.commit()
        cur.close()
        conn.close()


# ── READY TESTS ────────────────────────────────────────────────────────────

def db_load_ready_tests() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM ready_tests")
    rows = cur.fetchall()
    result = {r[0]: _row_to_dict(cur, r) for r in rows}
    cur.close()
    conn.close()
    return result


def db_add_to_ready_tests(test_id: str, admin_id: int) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM ready_tests WHERE test_id=%s", (test_id,))
    exists = cur.fetchone()
    cur.close()
    conn.close()
    if exists:
        return False
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO ready_tests (test_id, added_by, added_date) VALUES (%s, %s, %s)",
            (test_id, admin_id, datetime.now().isoformat())
        )
        conn.commit()
        cur.close()
        conn.close()
    return True


def db_remove_from_ready_tests(test_id: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM ready_tests WHERE test_id=%s", (test_id,))
    exists = cur.fetchone()
    cur.close()
    conn.close()
    if not exists:
        return False
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM ready_tests WHERE test_id=%s", (test_id,))
        conn.commit()
        cur.close()
        conn.close()
    return True


# ── ADMIN LOGS ─────────────────────────────────────────────────────────────

def db_log_admin_action(admin_id: int, admin_name: str, action: str, target_user, details: str):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO admin_logs (admin_id, admin_name, action, target_user, details, timestamp) VALUES (%s,%s,%s,%s,%s,%s)",
            (admin_id, admin_name, action, str(target_user), details, datetime.now().isoformat())
        )
        cur.execute("""
            DELETE FROM admin_logs WHERE id NOT IN (
                SELECT id FROM admin_logs ORDER BY id DESC LIMIT 500
            )
        """)
        conn.commit()
        cur.close()
        conn.close()


def db_get_admin_logs(limit=50) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM admin_logs ORDER BY id DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    result = [_row_to_dict(cur, r) for r in rows]
    cur.close()
    conn.close()
    return result


def db_clear_admin_logs():
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DELETE FROM admin_logs")
        conn.commit()
        cur.close()
        conn.close()


# ── TEST RESULTS ───────────────────────────────────────────────────────────

def db_save_test_result(test_id, group_key, user_id, username, score, total, time_spent):
    with _lock:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO test_results (test_id, group_key, user_id, username, score, total, time_spent, date) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (test_id, group_key, user_id, username, score, total, round(time_spent, 1), datetime.now().isoformat())
        )
        conn.commit()
        cur.close()
        conn.close()


def db_get_leaderboard(test_id, group_key, limit=10) -> list:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM test_results WHERE test_id=%s AND group_key=%s ORDER BY score DESC, time_spent ASC LIMIT %s",
        (test_id, group_key, limit)
    )
    rows = cur.fetchall()
    result = [_row_to_dict(cur, r) for r in rows]
    cur.close()
    conn.close()
    return result
