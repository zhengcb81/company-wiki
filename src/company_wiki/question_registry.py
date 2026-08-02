"""
question_registry.py — 问题注册表

管理研究问题的状态、优先级、回答状态和版本。
问题有稳定 ID，不随文本变更。
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .domain import Question, AnswerState


_SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS questions (
    question_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    owner TEXT,
    priority TEXT DEFAULT 'medium',
    status TEXT DEFAULT 'active',
    answer_state TEXT DEFAULT 'unanswered',
    evidence_type TEXT DEFAULT 'news',
    version INTEGER DEFAULT 1,
    created_at TEXT NOT NULL,
    last_answered_at TEXT,
    expires_at TEXT,
    supersedes TEXT,
    supporting_claims TEXT DEFAULT '[]',
    refuting_claims TEXT DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_questions_owner ON questions(owner);
CREATE INDEX IF NOT EXISTS idx_questions_status ON questions(status);
CREATE INDEX IF NOT EXISTS idx_questions_answer_state ON questions(answer_state);
"""


class QuestionRegistry:
    """
    问题注册表。

    管理研究问题的生命周期：创建、回答、过期、替代。
    """

    def __init__(self, db_path: Path):
        self._db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self):
        current_version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        if current_version < _SCHEMA_VERSION:
            self._conn.executescript(_SCHEMA_SQL)
            self._conn.execute(f"PRAGMA user_version={_SCHEMA_VERSION}")
            self._conn.commit()

    def close(self):
        self._conn.close()

    # ── CRUD ──────────────────────────────

    def add(self, question: Question):
        """添加问题"""
        datetime.now().isoformat()
        self._conn.execute(
            """INSERT OR REPLACE INTO questions
               (question_id, text, owner, priority, status, answer_state,
                evidence_type, version, created_at, last_answered_at,
                expires_at, supersedes, supporting_claims, refuting_claims)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '[]', '[]')""",
            (
                question.id, question.text, question.owner,
                question.priority, question.status, question.answer_state.value,
                question.evidence_type, question.version,
                question.created_at.isoformat(),
                question.last_answered_at.isoformat() if question.last_answered_at else None,
                question.expires_at.isoformat() if question.expires_at else None,
                question.supersedes,
            ),
        )
        self._conn.commit()

    def get(self, question_id: str) -> Optional[Question]:
        """获取问题"""
        row = self._conn.execute(
            "SELECT * FROM questions WHERE question_id = ?", (question_id,)
        ).fetchone()
        if not row:
            return None
        return self._row_to_question(row)

    def list_by_owner(self, owner: str, status: str = "active") -> list[Question]:
        """按 owner 列出问题"""
        rows = self._conn.execute(
            "SELECT * FROM questions WHERE owner = ? AND status = ? ORDER BY priority DESC, created_at",
            (owner, status),
        ).fetchall()
        return [self._row_to_question(r) for r in rows]

    def list_all(self, status: str = "active") -> list[Question]:
        """列出所有问题"""
        rows = self._conn.execute(
            "SELECT * FROM questions WHERE status = ? ORDER BY owner, priority DESC",
            (status,),
        ).fetchall()
        return [self._row_to_question(r) for r in rows]

    def count_by_answer_state(self) -> dict[str, int]:
        """按回答状态统计"""
        rows = self._conn.execute(
            "SELECT answer_state, COUNT(*) as cnt FROM questions WHERE status = 'active' GROUP BY answer_state"
        ).fetchall()
        return {row["answer_state"]: row["cnt"] for row in rows}

    # ── 状态更新 ──────────────────────────────

    def update_answer_state(
        self,
        question_id: str,
        state: AnswerState,
        supporting_claim_id: str = None,
        refuting_claim_id: str = None,
    ):
        """更新问题回答状态"""
        now = datetime.now().isoformat()
        row = self._conn.execute(
            "SELECT supporting_claims, refuting_claims FROM questions WHERE question_id = ?",
            (question_id,),
        ).fetchone()
        if not row:
            return

        supporting = json.loads(row["supporting_claims"])
        refuting = json.loads(row["refuting_claims"])

        if supporting_claim_id and supporting_claim_id not in supporting:
            supporting.append(supporting_claim_id)
        if refuting_claim_id and refuting_claim_id not in refuting:
            refuting.append(refuting_claim_id)

        self._conn.execute(
            """UPDATE questions SET answer_state = ?, supporting_claims = ?,
               refuting_claims = ?, last_answered_at = ? WHERE question_id = ?""",
            (state.value, json.dumps(supporting), json.dumps(refuting), now, question_id),
        )
        self._conn.commit()

    def archive(self, question_id: str):
        """归档问题"""
        self._conn.execute(
            "UPDATE questions SET status = 'archived' WHERE question_id = ?",
            (question_id,),
        )
        self._conn.commit()

    def supersedes(self, old_id: str, new_id: str):
        """标记旧问题被新问题替代"""
        self._conn.execute(
            "UPDATE questions SET status = 'superseded' WHERE question_id = ?",
            (old_id,),
        )
        self._conn.execute(
            "UPDATE questions SET supersedes = ? WHERE question_id = ?",
            (old_id, new_id),
        )
        self._conn.commit()

    # ── 内部方法 ──────────────────────────────

    def _row_to_question(self, row: sqlite3.Row) -> Question:
        return Question(
            id=row["question_id"],
            text=row["text"],
            owner=row["owner"],
            priority=row["priority"],
            status=row["status"],
            answer_state=AnswerState(row["answer_state"]),
            evidence_type=row["evidence_type"],
            version=row["version"],
            created_at=datetime.fromisoformat(row["created_at"]),
            last_answered_at=datetime.fromisoformat(row["last_answered_at"]) if row["last_answered_at"] else None,
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
            supersedes=row["supersedes"],
        )


def load_questions_from_pilot(pilot_path: Path) -> list[Question]:
    """从 pilot.yaml 加载问题列表"""
    import yaml
    if not pilot_path.exists():
        return []
    with open(pilot_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    questions = []
    for q_data in data.get("questions", []):
        q = Question(
            id=q_data.get("id", ""),
            text=q_data.get("text", ""),
            owner=q_data.get("owner"),
            priority=q_data.get("priority", "medium"),
            evidence_type=q_data.get("evidence_type", "news"),
        )
        questions.append(q)
    return questions
