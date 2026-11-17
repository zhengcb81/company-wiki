"""Isolated test host; SQLite uniqueness models a real host's atomic submission."""

from contextlib import closing
import json
import sqlite3
import sys


def main():
    request = json.load(sys.stdin)
    key, kind = request["action_id"], request["kind"]
    reply = {"schema_version": "feedback-action-result/1", "action_id": key,
             "request_digest": request["request_digest"], "state": "absent"}
    with closing(sqlite3.connect(sys.argv[1], timeout=10)) as conn, conn:
        conn.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, kind TEXT, reply TEXT)")
        if request["method"] == "submit":
            result = {"observe": {"recorded": True},
                      "triage": {"decision": "repair", "issue_ref": "reader/quality", "generation": "1"},
                      "repair": {"fixed_version": "v2"}, "replay": {"verdict": "verified", "verified_version": "v2",
                                                                   "evidence_ref": "consumer/check"},
                      "report": {"recorded": True}}[kind]
            done = {**reply, "state": "done", "result": result}
            inserted = conn.execute("INSERT OR IGNORE INTO jobs VALUES (?, ?, ?)",
                                    (key, kind, json.dumps(done))).rowcount
            if inserted and kind == "repair" and "--lose-reply" in sys.argv:
                return 7
        previous = conn.execute("SELECT reply FROM jobs WHERE id = ?", (key,)).fetchone()
    print(previous[0] if previous else json.dumps(reply))
    return 0


if __name__ == "__main__":
    sys.exit(main())
