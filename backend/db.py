from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from backend.config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def connection() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _hash_password(password: str, salt: str | None = None) -> str:
    target_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), target_salt.encode("ascii"), 310_000
    )
    return f"{target_salt}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return secrets.compare_digest(_hash_password(password, salt), stored)


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def initialize_database() -> None:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    with connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS password_reset_codes (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                code_hash TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                used_at TEXT,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_password_reset_user_time
                ON password_reset_codes(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS health_profiles (
                user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                gender TEXT DEFAULT '',
                birth_date TEXT DEFAULT '',
                blood_type TEXT DEFAULT '',
                height_cm REAL,
                allergies TEXT DEFAULT '[]',
                conditions TEXT DEFAULT '[]',
                medications TEXT DEFAULT '[]',
                family_history TEXT DEFAULT '[]',
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS health_records (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                measured_at TEXT NOT NULL,
                systolic INTEGER,
                diastolic INTEGER,
                heart_rate INTEGER,
                glucose REAL,
                spo2 INTEGER,
                weight_kg REAL,
                sleep_hours REAL,
                steps INTEGER,
                mood TEXT,
                note TEXT DEFAULT '',
                source TEXT DEFAULT 'manual',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_health_user_time
                ON health_records(user_id, measured_at DESC);

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                summary TEXT DEFAULT '',
                risk_level TEXT DEFAULT 'low',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_conversations_user_time
                ON conversations(user_id, updated_at DESC);

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL
                    REFERENCES conversations(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content TEXT NOT NULL,
                trace TEXT DEFAULT '{}',
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_time
                ON messages(conversation_id, created_at);

            CREATE TABLE IF NOT EXISTS triage_events (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                symptoms TEXT NOT NULL,
                level TEXT NOT NULL,
                score INTEGER NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_triage_user_time
                ON triage_events(user_id, created_at DESC);

            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                rating INTEGER NOT NULL,
                ease_score INTEGER NOT NULL,
                usefulness_score INTEGER NOT NULL,
                comments TEXT DEFAULT '',
                created_at TEXT NOT NULL
            );
            """
        )
    if settings.demo_mode:
        seed_demo()


def create_user(email: str, password: str, name: str) -> dict[str, Any]:
    user_id = str(uuid.uuid4())
    now = utc_now()
    with connection() as conn:
        conn.execute(
            "INSERT INTO users(id, email, password_hash, name, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email.lower().strip(), _hash_password(password), name.strip(), now),
        )
        conn.execute(
            """
            INSERT INTO health_profiles(user_id, updated_at)
            VALUES (?, ?)
            """,
            (user_id, now),
        )
    return get_user(user_id)  # type: ignore[return-value]


def authenticate(email: str, password: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),)
        ).fetchone()
    if not row or not _verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def update_account(
    user_id: str,
    current_password: str,
    new_email: str | None = None,
    new_password: str | None = None,
) -> dict[str, Any]:
    """Change email and/or password after verifying the current password."""
    email = (new_email or "").strip().lower()
    with connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            return {"ok": False, "error": "user_not_found"}
        if not _verify_password(current_password, row["password_hash"]):
            return {"ok": False, "error": "invalid_password"}

        assignments: list[str] = []
        values: list[Any] = []
        if email and email != row["email"]:
            duplicate = conn.execute(
                "SELECT id FROM users WHERE email = ? COLLATE NOCASE AND id <> ?",
                (email, user_id),
            ).fetchone()
            if duplicate:
                return {"ok": False, "error": "email_taken"}
            assignments.append("email = ?")
            values.append(email)
        if new_password:
            assignments.append("password_hash = ?")
            values.append(_hash_password(new_password))
        if not assignments:
            return {"ok": False, "error": "nothing_to_update"}

        values.append(user_id)
        conn.execute(
            f"UPDATE users SET {', '.join(assignments)} WHERE id = ?", values
        )
    return {"ok": True, "user": get_user(user_id)}


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.session_days)
    with connection() as conn:
        conn.execute(
            "INSERT INTO sessions(token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (_token_digest(token), user_id, expires.isoformat(), now.isoformat()),
        )
    return token


def get_user_by_session(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    with connection() as conn:
        row = conn.execute(
            """
            SELECT u.id, u.email, u.name, u.created_at, s.expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (_token_digest(token),),
        ).fetchone()
    if not row:
        return None
    if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
        delete_session(token)
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "created_at": row["created_at"],
    }


def delete_session(token: str | None) -> None:
    if not token:
        return
    with connection() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_digest(token),))


def get_user_by_email(email: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, created_at FROM users WHERE email = ? COLLATE NOCASE",
            (email.strip().lower(),),
        ).fetchone()
    return dict(row) if row else None


def issue_password_reset_code(
    user_id: str,
    code_hash: str,
    *,
    ttl_minutes: int = 10,
    cooldown_seconds: int = 60,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    with connection() as conn:
        latest = conn.execute(
            """
            SELECT created_at FROM password_reset_codes
            WHERE user_id = ? AND used_at IS NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id,),
        ).fetchone()
        if latest:
            try:
                elapsed = (now - datetime.fromisoformat(latest["created_at"])).total_seconds()
            except ValueError:
                elapsed = cooldown_seconds
            if elapsed < cooldown_seconds:
                return {
                    "ok": False,
                    "error": "cooldown",
                    "retry_after": max(1, int(cooldown_seconds - elapsed)),
                }

        conn.execute(
            "DELETE FROM password_reset_codes WHERE user_id = ?",
            (user_id,),
        )
        conn.execute(
            """
            INSERT INTO password_reset_codes(
                id, user_id, code_hash, expires_at, attempts, created_at
            ) VALUES (?, ?, ?, ?, 0, ?)
            """,
            (
                str(uuid.uuid4()),
                user_id,
                code_hash,
                (now + timedelta(minutes=ttl_minutes)).isoformat(),
                now.isoformat(),
            ),
        )
    return {"ok": True, "expires_in_minutes": ttl_minutes}


def invalidate_password_reset_codes(user_id: str) -> None:
    with connection() as conn:
        conn.execute(
            "DELETE FROM password_reset_codes WHERE user_id = ?",
            (user_id,),
        )


def reset_password_with_code(
    email: str,
    code_hash: str,
    new_password: str,
) -> dict[str, Any]:
    """Consume a reset code, update the password, and revoke all sessions."""
    now = datetime.now(timezone.utc)
    with connection() as conn:
        user = conn.execute(
            "SELECT id FROM users WHERE email = ? COLLATE NOCASE",
            (email.strip().lower(),),
        ).fetchone()
        if not user:
            return {"ok": False, "error": "invalid_code"}
        row = conn.execute(
            """
            SELECT * FROM password_reset_codes
            WHERE user_id = ? AND used_at IS NULL
            ORDER BY created_at DESC LIMIT 1
            """,
            (user["id"],),
        ).fetchone()
        if not row:
            return {"ok": False, "error": "invalid_code"}
        try:
            expired = datetime.fromisoformat(row["expires_at"]) <= now
        except ValueError:
            expired = True
        if expired:
            conn.execute(
                "UPDATE password_reset_codes SET used_at = ? WHERE id = ?",
                (now.isoformat(), row["id"]),
            )
            return {"ok": False, "error": "expired"}
        if row["attempts"] >= 5:
            conn.execute(
                "UPDATE password_reset_codes SET used_at = ? WHERE id = ?",
                (now.isoformat(), row["id"]),
            )
            return {"ok": False, "error": "too_many_attempts"}
        if not hmac.compare_digest(row["code_hash"], code_hash):
            attempts = int(row["attempts"]) + 1
            conn.execute(
                """
                UPDATE password_reset_codes
                SET attempts = ?, used_at = CASE WHEN ? >= 5 THEN ? ELSE used_at END
                WHERE id = ?
                """,
                (attempts, attempts, now.isoformat(), row["id"]),
            )
            return {"ok": False, "error": "invalid_code"}

        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (_hash_password(new_password), user["id"]),
        )
        conn.execute(
            "UPDATE password_reset_codes SET used_at = ? WHERE id = ?",
            (now.isoformat(), row["id"]),
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user["id"],))
    return {"ok": True}


def get_user(user_id: str) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT id, email, name, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def get_health_profile(user_id: str) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM health_profiles WHERE user_id = ?", (user_id,)
        ).fetchone()
    if not row:
        return {}
    result = dict(row)
    for key in ("allergies", "conditions", "medications", "family_history"):
        try:
            result[key] = json.loads(result.get(key) or "[]")
        except json.JSONDecodeError:
            result[key] = []
    return result


def update_health_profile(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    current = get_health_profile(user_id)
    merged = {**current, **data, "user_id": user_id, "updated_at": utc_now()}
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO health_profiles(
                user_id, gender, birth_date, blood_type, height_cm, allergies,
                conditions, medications, family_history, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                gender=excluded.gender,
                birth_date=excluded.birth_date,
                blood_type=excluded.blood_type,
                height_cm=excluded.height_cm,
                allergies=excluded.allergies,
                conditions=excluded.conditions,
                medications=excluded.medications,
                family_history=excluded.family_history,
                updated_at=excluded.updated_at
            """,
            (
                user_id,
                merged.get("gender", ""),
                merged.get("birth_date", ""),
                merged.get("blood_type", ""),
                merged.get("height_cm"),
                json.dumps(merged.get("allergies", []), ensure_ascii=False),
                json.dumps(merged.get("conditions", []), ensure_ascii=False),
                json.dumps(merged.get("medications", []), ensure_ascii=False),
                json.dumps(merged.get("family_history", []), ensure_ascii=False),
                merged["updated_at"],
            ),
        )
    return get_health_profile(user_id)


def add_health_record(user_id: str, data: dict[str, Any]) -> dict[str, Any]:
    record_id = str(uuid.uuid4())
    now = utc_now()
    fields = (
        "systolic",
        "diastolic",
        "heart_rate",
        "glucose",
        "spo2",
        "weight_kg",
        "sleep_hours",
        "steps",
        "mood",
        "note",
        "source",
    )
    values = [data.get(field) for field in fields]
    with connection() as conn:
        conn.execute(
            f"""
            INSERT INTO health_records(
                id, user_id, measured_at, {", ".join(fields)}, created_at
            ) VALUES (?, ?, ?, {", ".join("?" for _ in fields)}, ?)
            """,
            (
                record_id,
                user_id,
                data.get("measured_at") or now,
                *values,
                now,
            ),
        )
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM health_records WHERE id = ?", (record_id,)
        ).fetchone()
    return dict(row)


def list_health_records(user_id: str, limit: int = 30) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM health_records
            WHERE user_id = ?
            ORDER BY measured_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    return [dict(row) for row in rows]


def create_conversation(
    user_id: str, title: str = "新的健康咨询"
) -> dict[str, Any]:
    conversation_id = str(uuid.uuid4())
    now = utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO conversations(id, user_id, title, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, user_id, title[:80], now, now),
        )
    return get_conversation(user_id, conversation_id)  # type: ignore[return-value]


def list_conversations(user_id: str) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT c.*,
                   (SELECT content FROM messages m
                    WHERE m.conversation_id = c.id
                    ORDER BY m.created_at DESC LIMIT 1) AS last_message,
                   (SELECT count(*) FROM messages m
                    WHERE m.conversation_id = c.id) AS message_count
            FROM conversations c
            WHERE c.user_id = ?
            ORDER BY c.updated_at DESC
            """,
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(
    user_id: str, conversation_id: str
) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        ).fetchone()
        if not row:
            return None
        messages = conn.execute(
            """
            SELECT id, role, content, trace, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at
            """,
            (conversation_id,),
        ).fetchall()
    result = dict(row)
    output_messages = []
    for message in messages:
        item = dict(message)
        try:
            item["trace"] = json.loads(item.get("trace") or "{}")
        except json.JSONDecodeError:
            item["trace"] = {}
        output_messages.append(item)
    result["messages"] = output_messages
    return result


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message_id = str(uuid.uuid4())
    now = utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO messages(id, conversation_id, role, content, trace, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                conversation_id,
                role,
                content,
                json.dumps(trace or {}, ensure_ascii=False),
                now,
            ),
        )
    return {
        "id": message_id,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "trace": trace or {},
        "created_at": now,
    }


def update_conversation(
    conversation_id: str,
    *,
    title: str | None = None,
    summary: str | None = None,
    risk_level: str | None = None,
) -> None:
    updates = ["updated_at = ?"]
    values: list[Any] = [utc_now()]
    if title is not None:
        updates.append("title = ?")
        values.append(title[:80])
    if summary is not None:
        updates.append("summary = ?")
        values.append(summary[:1000])
    if risk_level is not None:
        updates.append("risk_level = ?")
        values.append(risk_level)
    values.append(conversation_id)
    with connection() as conn:
        conn.execute(
            f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
            values,
        )


def delete_conversation(user_id: str, conversation_id: str) -> bool:
    with connection() as conn:
        cursor = conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?",
            (conversation_id, user_id),
        )
    return cursor.rowcount > 0


def conversation_context(conversation_id: str, limit: int = 12) -> list[dict[str, str]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT role, content FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (conversation_id, limit),
        ).fetchall()
    return [dict(row) for row in reversed(rows)]


def add_triage_event(
    user_id: str,
    symptoms: str,
    result: dict[str, Any],
) -> dict[str, Any]:
    event_id = str(uuid.uuid4())
    created_at = utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO triage_events(
                id, user_id, symptoms, level, score, result_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                user_id,
                symptoms,
                str(result.get("level", "low")),
                int(result.get("score", 0)),
                json.dumps(result, ensure_ascii=False),
                created_at,
            ),
        )
    return {"id": event_id, "created_at": created_at, **result}


def list_triage_events(user_id: str, limit: int = 30) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, symptoms, level, score, result_json, created_at
            FROM triage_events
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
    events = []
    for row in rows:
        try:
            result = json.loads(row["result_json"])
        except json.JSONDecodeError:
            result = {}
        events.append(
            {
                "id": row["id"],
                "symptoms": row["symptoms"],
                "level": row["level"],
                "score": row["score"],
                "result": result,
                "created_at": row["created_at"],
            }
        )
    return events


def add_feedback(
    user_id: str,
    *,
    rating: int,
    ease_score: int,
    usefulness_score: int,
    comments: str,
) -> dict[str, Any]:
    feedback_id = str(uuid.uuid4())
    created_at = utc_now()
    with connection() as conn:
        conn.execute(
            """
            INSERT INTO feedback(
                id, user_id, rating, ease_score, usefulness_score, comments, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                user_id,
                rating,
                ease_score,
                usefulness_score,
                comments[:1000],
                created_at,
            ),
        )
    return {
        "id": feedback_id,
        "rating": rating,
        "ease_score": ease_score,
        "usefulness_score": usefulness_score,
        "comments": comments[:1000],
        "created_at": created_at,
    }


def feedback_summary(user_id: str) -> dict[str, Any]:
    with connection() as conn:
        row = conn.execute(
            """
            SELECT count(*) AS count,
                   coalesce(avg(rating), 0) AS rating,
                   coalesce(avg(ease_score), 0) AS ease,
                   coalesce(avg(usefulness_score), 0) AS usefulness
            FROM feedback WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
    return {
        "count": row["count"],
        "rating": round(float(row["rating"]), 2),
        "ease": round(float(row["ease"]), 2),
        "usefulness": round(float(row["usefulness"]), 2),
    }


def seed_demo() -> None:
    email = "demo@qihuang.local"
    with connection() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE email = ?", (email,)
        ).fetchone()
    if existing:
        return

    user = create_user(email, "demo1234", "林知夏")
    update_health_profile(
        user["id"],
        {
            "gender": "女",
            "birth_date": "1997-06-18",
            "blood_type": "A",
            "height_cm": 165,
            "allergies": ["青霉素"],
            "conditions": ["轻度缺铁性贫血"],
            "medications": ["维生素C"],
            "family_history": ["高血压（父亲）"],
        },
    )
    now = datetime.now(timezone.utc)
    readings = [
        (0, 118, 76, 72, 5.4, 99, 52.0, 7.3, 6840, "平静"),
        (1, 121, 78, 76, 5.6, 99, 52.1, 6.8, 7560, "良好"),
        (2, 116, 74, 70, 5.2, 98, 51.9, 7.6, 8240, "愉悦"),
        (3, 124, 81, 84, 5.8, 98, 52.0, 6.1, 5210, "疲惫"),
        (4, 119, 77, 74, 5.5, 99, 51.8, 7.1, 7120, "平静"),
        (5, 122, 79, 78, 6.1, 99, 51.9, 7.4, 8630, "良好"),
        (6, 117, 75, 71, 5.3, 99, 51.8, 7.8, 9120, "愉悦"),
    ]
    for offset, sys, dia, hr, glucose, spo2, weight, sleep, steps, mood in readings:
        add_health_record(
            user["id"],
            {
                "measured_at": (now - timedelta(days=offset, hours=2)).isoformat(),
                "systolic": sys,
                "diastolic": dia,
                "heart_rate": hr,
                "glucose": glucose,
                "spo2": spo2,
                "weight_kg": weight,
                "sleep_hours": sleep,
                "steps": steps,
                "mood": mood,
                "source": "智能设备",
            },
        )

    conversation = create_conversation(user["id"], "最近头晕，可能是什么原因？")
    add_message(
        conversation["id"],
        "user",
        "我最近起床时偶尔会头晕，平时血压偏低，需要担心吗？",
    )
    add_message(
        conversation["id"],
        "assistant",
        "起床时短暂头晕可能与体位性低血压、睡眠不足或贫血有关。建议先缓慢起身、补充水分并记录血压变化。如果出现晕厥、胸痛、单侧肢体无力或说话不清，请立即就医。",
        {
            "entities": [{"name": "头晕", "type": "Symptom"}],
            "risk_level": "low",
            "evidence_count": 3,
        },
    )
    update_conversation(
        conversation["id"],
        summary="用户咨询起床时偶发头晕，伴平时血压偏低；已建议监测血压并说明急症警示。",
        risk_level="low",
    )

