"""Reset the demo account to a clean seeded state.

Competition demos are easy to corrupt: extra conversations, edited vitals,
leftover feedback. Run this before presenting to restore a known state.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend import db


DEMO_EMAIL = "demo@qihuang.local"


def main() -> None:
    db.initialize_database()
    with db.connection() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE email = ?", (DEMO_EMAIL,)
        ).fetchone()
        if not row:
            db.seed_demo()
            print("demo user did not exist; seeded a fresh demo profile")
            return
        user_id = row["id"]
        conn.execute(
            "DELETE FROM messages WHERE conversation_id IN (SELECT id FROM conversations WHERE user_id = ?)",
            (user_id,),
        )
        conn.execute("DELETE FROM conversations WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM health_records WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM triage_events WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM feedback WHERE user_id = ?", (user_id,))
        conn.execute(
            "DELETE FROM health_profiles WHERE user_id = ?", (user_id,)
        )
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.seed_demo()
    print("demo profile reset: demo@qihuang.local / demo1234")


if __name__ == "__main__":
    main()
