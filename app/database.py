import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "decisionmemory.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_code TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        department TEXT NOT NULL DEFAULT 'General',
        category TEXT NOT NULL DEFAULT 'Strategy',
        problem_context TEXT NOT NULL,
        decision_text TEXT NOT NULL,
        reasoning TEXT NOT NULL,
        rejected_alternatives TEXT DEFAULT '[]', -- JSON string
        owner_name TEXT NOT NULL,
        owner_role TEXT DEFAULT 'Decision Owner',
        participants TEXT DEFAULT '[]',          -- JSON string
        source_type TEXT DEFAULT 'direct',      -- whatsapp, meeting, email, call, direct
        raw_source_text TEXT DEFAULT '',
        decision_date TEXT,
        deadline_date TEXT,
        budget_or_cost TEXT DEFAULT '',
        status TEXT DEFAULT 'ACTIVE',           -- DRAFT, ACTIVE, IMPLEMENTED, SUPERSEDED, REVOKED
        superseded_by_id INTEGER,
        supersedes_id INTEGER,
        expected_outcome TEXT DEFAULT '',
        outcome_status TEXT DEFAULT 'PENDING_EVALUATION', -- PENDING_EVALUATION, SUCCESS, PARTIAL_SUCCESS, FAILED, ABANDONED
        outcome_notes TEXT DEFAULT '',
        outcome_evaluated_at TEXT,
        outcome_evaluated_by TEXT,
        lessons_learned TEXT DEFAULT '',
        tags TEXT DEFAULT '[]',                 -- JSON string
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (superseded_by_id) REFERENCES decisions(id) ON DELETE SET NULL,
        FOREIGN KEY (supersedes_id) REFERENCES decisions(id) ON DELETE SET NULL
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        assignee TEXT NOT NULL,
        due_date TEXT,
        priority TEXT DEFAULT 'MEDIUM',         -- HIGH, MEDIUM, LOW
        status TEXT DEFAULT 'PENDING',          -- PENDING, IN_PROGRESS, COMPLETED, BLOCKED
        completed_at TEXT,
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decision_conflicts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id_a INTEGER NOT NULL,
        decision_id_b INTEGER NOT NULL,
        conflict_type TEXT NOT NULL,            -- DIRECT_CONFLICT, REPEATED_DUPLICATE, POLICY_COLLISION, VENDOR_OVERLAP
        severity TEXT NOT NULL DEFAULT 'MEDIUM',-- HIGH, MEDIUM, LOW
        similarity_score REAL DEFAULT 0.0,
        explanation TEXT NOT NULL,
        suggested_action TEXT DEFAULT '',
        status TEXT DEFAULT 'UNRESOLVED',       -- UNRESOLVED, RESOLVED_SUPERSEDED, RESOLVED_EXCEPTION, DISMISSED
        resolution_notes TEXT DEFAULT '',
        detected_at TEXT NOT NULL,
        FOREIGN KEY (decision_id_a) REFERENCES decisions(id) ON DELETE CASCADE,
        FOREIGN KEY (decision_id_b) REFERENCES decisions(id) ON DELETE CASCADE
    );
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        decision_id INTEGER,
        action TEXT NOT NULL,
        details TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        FOREIGN KEY (decision_id) REFERENCES decisions(id) ON DELETE CASCADE
    );
    """)

    conn.commit()
    conn.close()

def parse_json_safely(val, default):
    if not val:
        return default
    if isinstance(val, (list, dict)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default

def row_to_decision_dict(row: sqlite3.Row, include_stats: bool = True) -> Dict[str, Any]:
    d = dict(row)
    d["rejected_alternatives"] = parse_json_safely(d.get("rejected_alternatives"), [])
    d["participants"] = parse_json_safely(d.get("participants"), [])
    d["tags"] = parse_json_safely(d.get("tags"), [])

    if include_stats:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total, SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed FROM tasks WHERE decision_id = ?", (d["id"],))
        task_res = cursor.fetchone()
        conn.close()
        total_tasks = task_res["total"] if task_res else 0
        completed_tasks = task_res["completed"] if (task_res and task_res["completed"] is not None) else 0
        d["task_count"] = total_tasks
        d["completed_task_count"] = completed_tasks
        if total_tasks > 0:
            d["health_score"] = int((completed_tasks / total_tasks) * 100)
        else:
            d["health_score"] = 100 if d["status"] in ("IMPLEMENTED", "ACTIVE") else 50
    return d

def get_all_decisions(
    department: Optional[str] = None,
    status: Optional[str] = None,
    outcome_status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM decisions WHERE 1=1"
    params = []

    if department and department.lower() != "all":
        query += " AND LOWER(department) = LOWER(?)"
        params.append(department)

    if status and status.lower() != "all":
        query += " AND UPPER(status) = UPPER(?)"
        params.append(status)

    if outcome_status and outcome_status.lower() != "all":
        query += " AND UPPER(outcome_status) = UPPER(?)"
        params.append(outcome_status)

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query += """ AND (
            LOWER(title) LIKE ? OR 
            LOWER(decision_text) LIKE ? OR 
            LOWER(reasoning) LIKE ? OR 
            LOWER(problem_context) LIKE ? OR 
            LOWER(owner_name) LIKE ? OR 
            LOWER(tags) LIKE ? OR
            LOWER(decision_code) LIKE ?
        )"""
        params.extend([term] * 7)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    return [row_to_decision_dict(r) for r in rows]

def get_decision_by_id(decision_id: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM decisions WHERE id = ?", (decision_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    d = row_to_decision_dict(row)

    # Fetch tasks
    cursor.execute("SELECT * FROM tasks WHERE decision_id = ? ORDER BY id ASC", (decision_id,))
    task_rows = cursor.fetchall()
    d["tasks"] = [dict(t) for t in task_rows]

    # Fetch audit logs
    cursor.execute("SELECT * FROM audit_logs WHERE decision_id = ? ORDER BY id DESC", (decision_id,))
    log_rows = cursor.fetchall()
    d["audit_logs"] = [dict(l) for l in log_rows]

    # Fetch active conflicts
    cursor.execute("""
        SELECT c.*, 
               d1.decision_code as code_a, d1.title as title_a,
               d2.decision_code as code_b, d2.title as title_b
        FROM decision_conflicts c
        JOIN decisions d1 ON c.decision_id_a = d1.id
        JOIN decisions d2 ON c.decision_id_b = d2.id
        WHERE (c.decision_id_a = ? OR c.decision_id_b = ?) AND c.status = 'UNRESOLVED'
    """, (decision_id, decision_id))
    conflict_rows = cursor.fetchall()
    d["active_conflicts"] = [dict(c) for c in conflict_rows]

    conn.close()
    return d

def get_decision_count() -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM decisions")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def generate_decision_code() -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(id) FROM decisions")
    max_id = cursor.fetchone()[0] or 0
    conn.close()
    year = datetime.now().year
    return f"DEC-{year}-{(max_id + 1):03d}"

def insert_decision(data: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()

    decision_code = data.get("decision_code") or generate_decision_code()
    rejected_alts_json = json.dumps(data.get("rejected_alternatives", []))
    participants_json = json.dumps(data.get("participants", []))
    tags_json = json.dumps(data.get("tags", []))

    cursor.execute("""
        INSERT INTO decisions (
            decision_code, title, department, category, problem_context,
            decision_text, reasoning, rejected_alternatives, owner_name, owner_role,
            participants, source_type, raw_source_text, decision_date, deadline_date,
            budget_or_cost, status, supersedes_id, expected_outcome, outcome_status,
            outcome_notes, lessons_learned, tags, created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?
        )
    """, (
        decision_code,
        data["title"],
        data.get("department", "General"),
        data.get("category", "Strategy"),
        data.get("problem_context", ""),
        data["decision_text"],
        data.get("reasoning", ""),
        rejected_alts_json,
        data.get("owner_name", "Unassigned"),
        data.get("owner_role", "Decision Owner"),
        participants_json,
        data.get("source_type", "direct"),
        data.get("raw_source_text", ""),
        data.get("decision_date") or datetime.now().strftime("%Y-%m-%d"),
        data.get("deadline_date"),
        data.get("budget_or_cost", ""),
        data.get("status", "ACTIVE"),
        data.get("supersedes_id"),
        data.get("expected_outcome", ""),
        data.get("outcome_status", "PENDING_EVALUATION"),
        data.get("outcome_notes", ""),
        data.get("lessons_learned", ""),
        tags_json,
        now_str,
        now_str
    ))
    decision_id = cursor.lastrowid

    # If superseding an older decision, update that older decision's status and superseded_by_id
    if data.get("supersedes_id"):
        cursor.execute("""
            UPDATE decisions 
            SET status = 'SUPERSEDED', superseded_by_id = ?, updated_at = ?
            WHERE id = ?
        """, (decision_id, now_str, data["supersedes_id"]))

    # Insert Tasks
    tasks = data.get("tasks", [])
    for t in tasks:
        cursor.execute("""
            INSERT INTO tasks (
                decision_id, title, description, assignee, due_date, priority, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            decision_id,
            t.get("title", "Task"),
            t.get("description", ""),
            t.get("assignee", data.get("owner_name", "Unassigned")),
            t.get("due_date") or data.get("deadline_date"),
            t.get("priority", "MEDIUM"),
            t.get("status", "PENDING"),
            now_str,
            now_str
        ))

    # Audit log
    cursor.execute("""
        INSERT INTO audit_logs (decision_id, action, details, timestamp)
        VALUES (?, 'CREATED', ?, ?)
    """, (decision_id, f"Decision created with code {decision_code} via {data.get('source_type', 'direct')}", now_str))

    conn.commit()
    conn.close()
    return decision_id

def update_decision(decision_id: int, updates: Dict[str, Any]) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()

    fields = []
    values = []

    field_map = {
        "title": "title", "department": "department", "category": "category",
        "problem_context": "problem_context", "decision_text": "decision_text",
        "reasoning": "reasoning", "owner_name": "owner_name", "owner_role": "owner_role",
        "deadline_date": "deadline_date", "budget_or_cost": "budget_or_cost",
        "status": "status", "supersedes_id": "supersedes_id",
        "expected_outcome": "expected_outcome", "outcome_status": "outcome_status",
        "outcome_notes": "outcome_notes", "lessons_learned": "lessons_learned"
    }

    for k, col in field_map.items():
        if k in updates and updates[k] is not None:
            fields.append(f"{col} = ?")
            values.append(updates[k])

    if "rejected_alternatives" in updates and updates["rejected_alternatives"] is not None:
        fields.append("rejected_alternatives = ?")
        values.append(json.dumps(updates["rejected_alternatives"]))

    if "participants" in updates and updates["participants"] is not None:
        fields.append("participants = ?")
        values.append(json.dumps(updates["participants"]))

    if "tags" in updates and updates["tags"] is not None:
        fields.append("tags = ?")
        values.append(json.dumps(updates["tags"]))

    if not fields:
        conn.close()
        return True

    fields.append("updated_at = ?")
    values.append(now_str)
    values.append(decision_id)

    query = f"UPDATE decisions SET {', '.join(fields)} WHERE id = ?"
    cursor.execute(query, values)

    # Audit log
    cursor.execute("""
        INSERT INTO audit_logs (decision_id, action, details, timestamp)
        VALUES (?, 'UPDATED', ?, ?)
    """, (decision_id, f"Updated fields: {list(updates.keys())}", now_str))

    conn.commit()
    conn.close()
    return True

def record_outcome(decision_id: int, outcome_status: str, outcome_notes: str, lessons_learned: str, evaluated_by: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()

    cursor.execute("""
        UPDATE decisions 
        SET outcome_status = ?,
            outcome_notes = ?,
            lessons_learned = ?,
            outcome_evaluated_at = ?,
            outcome_evaluated_by = ?,
            status = CASE WHEN ? = 'SUCCESS' THEN 'IMPLEMENTED' ELSE status END,
            updated_at = ?
        WHERE id = ?
    """, (outcome_status, outcome_notes, lessons_learned, now_str, evaluated_by, outcome_status, now_str, decision_id))

    cursor.execute("""
        INSERT INTO audit_logs (decision_id, action, details, timestamp)
        VALUES (?, 'OUTCOME_RECORDED', ?, ?)
    """, (decision_id, f"Outcome set to {outcome_status} by {evaluated_by}. Notes: {outcome_notes[:100]}", now_str))

    conn.commit()
    conn.close()
    return True

def add_task(decision_id: int, task_data: Dict[str, Any]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()

    cursor.execute("""
        INSERT INTO tasks (
            decision_id, title, description, assignee, due_date, priority, status, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        decision_id,
        task_data["title"],
        task_data.get("description", ""),
        task_data["assignee"],
        task_data.get("due_date"),
        task_data.get("priority", "MEDIUM"),
        task_data.get("status", "PENDING"),
        now_str,
        now_str
    ))
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id

def update_task(task_id: int, updates: Dict[str, Any]) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().isoformat()

    fields = []
    values = []
    for k in ["title", "description", "assignee", "due_date", "priority", "status", "notes"]:
        if k in updates and updates[k] is not None:
            fields.append(f"{k} = ?")
            values.append(updates[k])

    if updates.get("status") == "COMPLETED":
        fields.append("completed_at = ?")
        values.append(now_str)

    if not fields:
        conn.close()
        return True

    fields.append("updated_at = ?")
    values.append(now_str)
    values.append(task_id)

    cursor.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return True

def get_all_tasks(status: Optional[str] = None, assignee: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT t.*, d.decision_code, d.title as decision_title, d.department as decision_department
        FROM tasks t
        JOIN decisions d ON t.decision_id = d.id
        WHERE 1=1
    """
    params = []
    if status and status.lower() != "all":
        query += " AND UPPER(t.status) = UPPER(?)"
        params.append(status)
    if assignee and assignee.lower() != "all":
        query += " AND LOWER(t.assignee) = LOWER(?)"
        params.append(assignee)

    query += " ORDER BY CASE t.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, t.due_date ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_dashboard_stats() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()

    # Decisions count
    cursor.execute("SELECT COUNT(*) FROM decisions")
    total_decisions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM decisions WHERE status = 'ACTIVE'")
    active_decisions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM decisions WHERE status = 'IMPLEMENTED'")
    implemented_decisions = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM decisions WHERE status = 'SUPERSEDED'")
    superseded_decisions = cursor.fetchone()[0]

    # Tasks count
    cursor.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'COMPLETED'")
    completed_tasks = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status != 'COMPLETED'")
    pending_tasks = cursor.fetchone()[0]

    today_str = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT COUNT(*) FROM tasks WHERE status != 'COMPLETED' AND due_date IS NOT NULL AND due_date < ?", (today_str,))
    overdue_tasks = cursor.fetchone()[0]

    # Conflicts
    cursor.execute("SELECT COUNT(*) FROM decision_conflicts WHERE status = 'UNRESOLVED'")
    unresolved_conflicts = cursor.fetchone()[0]

    # Outcomes
    cursor.execute("SELECT COUNT(*) FROM decisions WHERE outcome_status = 'PENDING_EVALUATION' AND status IN ('ACTIVE', 'IMPLEMENTED')")
    pending_outcomes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM decisions WHERE outcome_status = 'SUCCESS'")
    success_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM decisions WHERE outcome_status IN ('SUCCESS', 'PARTIAL_SUCCESS', 'FAILED')")
    evaluated_total = cursor.fetchone()[0]
    success_rate = round((success_count / evaluated_total * 100), 1) if evaluated_total > 0 else 100.0

    # Department breakdown
    cursor.execute("SELECT department, COUNT(*) as cnt FROM decisions GROUP BY department")
    dept_rows = cursor.fetchall()
    decisions_by_dept = {r["department"]: r["cnt"] for r in dept_rows}

    # Status breakdown
    cursor.execute("SELECT status, COUNT(*) as cnt FROM decisions GROUP BY status")
    status_rows = cursor.fetchall()
    decisions_by_status = {r["status"]: r["cnt"] for r in status_rows}

    # Recent activity logs
    cursor.execute("""
        SELECT a.*, d.decision_code, d.title as decision_title
        FROM audit_logs a
        LEFT JOIN decisions d ON a.decision_id = d.id
        ORDER BY a.id DESC LIMIT 10
    """)
    activity_rows = cursor.fetchall()
    recent_activity = [dict(r) for r in activity_rows]

    conn.close()
    return {
        "total_decisions": total_decisions,
        "active_decisions": active_decisions,
        "implemented_decisions": implemented_decisions,
        "superseded_decisions": superseded_decisions,
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "pending_tasks": pending_tasks,
        "overdue_tasks": overdue_tasks,
        "unresolved_conflicts": unresolved_conflicts,
        "pending_outcomes": pending_outcomes,
        "success_rate_percent": success_rate,
        "decisions_by_dept": decisions_by_dept,
        "decisions_by_status": decisions_by_status,
        "recent_activity": recent_activity
    }
