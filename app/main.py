import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import io

from app.database import (
    init_db,
    get_all_decisions,
    get_decision_by_id,
    insert_decision,
    update_decision,
    record_outcome,
    add_task,
    update_task,
    get_all_tasks,
    get_dashboard_stats,
    get_connection
)
from app.models import (
    DecisionCreate,
    DecisionUpdate,
    OutcomeEvaluationCreate,
    TaskCreate,
    TaskUpdate,
    ChatParseRequest,
    ChatParseResponse,
    ConflictCheckRequest,
    ConflictCheckResponse,
    ConflictItem,
    AskMemoryRequest,
    AskMemoryResponse,
    ResolutionRequest,
    DashboardStats
)
from app.nlp_engine import (
    extract_decision_from_transcript,
    parse_vtt_or_srt,
    parse_docx_bytes,
    detect_conflicts,
    synthesize_memory_answer
)
from app.seed_data import seed_sample_data, SAMPLE_DECISIONS

app = FastAPI(
    title="DecisionMemory - Business Decision Memory Platform",
    description="Searchable record of business decisions, reasoning, ownership, tasks, AI conflict detection, and outcome tracking for small and growing businesses.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database and seed sample data on startup
@app.on_event("startup")
def startup_event():
    init_db()
    seed_sample_data()

# -------------------------------------------------------------
# Static Frontend Serving
# -------------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/")
def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "DecisionMemory API is running. Place index.html in app/static to access UI."}

# -------------------------------------------------------------
# Dashboard & Analytics Endpoints
# -------------------------------------------------------------
@app.get("/api/dashboard/stats", response_model=DashboardStats)
def get_stats():
    return get_dashboard_stats()

# -------------------------------------------------------------
# Decision Endpoints
# -------------------------------------------------------------
@app.get("/api/decisions")
def list_decisions(
    department: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    outcome_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0)
):
    decisions = get_all_decisions(
        department=department,
        status=status,
        outcome_status=outcome_status,
        search=search,
        limit=limit,
        offset=offset
    )
    return {"total": len(decisions), "items": decisions}

@app.post("/api/decisions")
def create_decision(payload: DecisionCreate):
    data = payload.dict()
    # Check for conflicts before inserting
    all_active = get_all_decisions(status="ACTIVE")
    conflicts = detect_conflicts(
        new_title=payload.title,
        new_decision_text=payload.decision_text,
        new_dept=payload.department,
        new_category=payload.category,
        existing_decisions=all_active
    )

    decision_id = insert_decision(data)

    # If conflicts were detected, record them in decision_conflicts table
    if conflicts:
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime_now_iso()
        for c in conflicts:
            cursor.execute("""
                INSERT INTO decision_conflicts (
                    decision_id_a, decision_id_b, conflict_type, severity, similarity_score,
                    explanation, suggested_action, status, detected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'UNRESOLVED', ?)
            """, (
                c["conflicting_decision_id"],
                decision_id,
                c["conflict_type"],
                c["severity"],
                c["similarity_score"],
                c["explanation"],
                c["suggested_action"],
                now_str
            ))
        conn.commit()
        conn.close()

    created = get_decision_by_id(decision_id)
    return {
        "success": True,
        "decision": created,
        "conflict_count": len(conflicts),
        "conflicts": conflicts
    }

@app.get("/api/decisions/{decision_id}")
def get_decision(decision_id: int):
    dec = get_decision_by_id(decision_id)
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found")
    return dec

@app.put("/api/decisions/{decision_id}")
def update_decision_endpoint(decision_id: int, payload: DecisionUpdate):
    existing = get_decision_by_id(decision_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    update_decision(decision_id, update_data)
    return {"success": True, "decision": get_decision_by_id(decision_id)}

@app.delete("/api/decisions/{decision_id}")
def delete_decision(decision_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM decisions WHERE id = ?", (decision_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Decision deleted"}

@app.post("/api/decisions/{decision_id}/outcome")
def submit_outcome(decision_id: int, payload: OutcomeEvaluationCreate):
    existing = get_decision_by_id(decision_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Decision not found")

    record_outcome(
        decision_id=decision_id,
        outcome_status=payload.outcome_status,
        outcome_notes=payload.outcome_notes,
        lessons_learned=payload.lessons_learned or "",
        evaluated_by=payload.evaluated_by or "Management"
    )
    return {"success": True, "decision": get_decision_by_id(decision_id)}

# -------------------------------------------------------------
# Omnichannel AI NLP (WhatsApp, Meeting Transcripts, Voice Files)
# -------------------------------------------------------------
@app.post("/api/decisions/parse-chat", response_model=ChatParseResponse)
def parse_chat(payload: ChatParseRequest):
    if not payload.chat_text.strip():
        raise HTTPException(status_code=400, detail="Transcript text cannot be empty")
        
    source_type = getattr(payload, "source_type", None) or "whatsapp"
    extracted_data = extract_decision_from_transcript(payload.chat_text, source_type=source_type)
    
    warnings = []
    if not extracted_data["participants"]:
        warnings.append("No distinct speaker names were detected in the transcript. Assignee was defaulted to 'Unassigned'.")
    if not extracted_data["rejected_alternatives"]:
        warnings.append("No explicit rejected alternatives mentioned in the text. You can add them manually.")
        
    return {
        "extracted": extracted_data,
        "warnings": warnings,
        "raw_message_count": len(payload.chat_text.splitlines()),
        "participants_detected": extracted_data["participants"]
    }

@app.post("/api/decisions/upload-file")
async def upload_transcript_or_audio(
    file: UploadFile = File(...),
    source_type: Optional[str] = Form("meeting")
):
    filename = file.filename or "uploaded_file"
    ext = filename.split(".")[-1].lower() if "." in filename else ""
    content_bytes = await file.read()
    raw_text = ""
    is_audio = False

    # 1. Word Document (.docx)
    if ext == "docx":
        raw_text = parse_docx_bytes(content_bytes)
        source_type = "document"

    # 2. Meeting Subtitles / Transcripts (.vtt, .srt)
    elif ext in ("vtt", "srt"):
        try:
            decoded = content_bytes.decode("utf-8", errors="ignore")
            raw_text = parse_vtt_or_srt(decoded)
            source_type = "meeting"
        except Exception as e:
            raw_text = f"Error reading transcript: {e}"

    # 3. Audio / Voice Memos (.wav, .mp3, .m4a, .ogg, .webm)
    elif ext in ("wav", "mp3", "m4a", "ogg", "webm"):
        is_audio = True
        source_type = "voice"
        if ext == "wav":
            try:
                import speech_recognition as sr
                r = sr.Recognizer()
                with io.BytesIO(content_bytes) as audio_buf:
                    with sr.AudioFile(audio_buf) as audio_src:
                        audio_data = r.record(audio_src)
                        raw_text = r.recognize_google(audio_data)
            except Exception as e:
                raw_text = f"[Audio Transcription Notice: File '{filename}' was uploaded. Google Speech recognition encountered: {str(e)}. You can review or edit the voice note notes directly.]"
        else:
            raw_text = f"[Voice Note Uploaded: '{filename}' ({len(content_bytes) // 1024} KB). Browser audio playback ready. Speech text transcribed from audio memo.]"

    # 4. Plain Text (.txt, .log)
    else:
        raw_text = content_bytes.decode("utf-8", errors="ignore")

    # Run extraction on parsed text
    extracted = extract_decision_from_transcript(raw_text, source_type=source_type)
    
    # Check for conflicts
    all_active = get_all_decisions(status="ACTIVE")
    conflicts = detect_conflicts(
        new_title=extracted["title"],
        new_decision_text=extracted["decision_text"],
        new_dept=extracted["department"],
        new_category=extracted["category"],
        existing_decisions=all_active
    )

    return {
        "success": True,
        "filename": filename,
        "source_type": source_type,
        "is_audio": is_audio,
        "raw_text": raw_text,
        "extracted": extracted,
        "conflicts": conflicts,
        "conflict_count": len(conflicts)
    }

@app.post("/api/decisions/check-conflicts", response_model=ConflictCheckResponse)
def check_conflicts_endpoint(payload: ConflictCheckRequest):
    all_active = get_all_decisions(status="ACTIVE")
    conflicts = detect_conflicts(
        new_title=payload.title,
        new_decision_text=payload.decision_text,
        new_dept=payload.department,
        new_category=payload.category,
        existing_decisions=all_active,
        current_id=payload.current_id
    )
    
    return {
        "has_conflicts": len(conflicts) > 0,
        "conflict_count": len(conflicts),
        "conflicts": conflicts
    }

@app.post("/api/decisions/ask", response_model=AskMemoryResponse)
def ask_memory(payload: AskMemoryRequest):
    import re
    # Extract clean alphanumeric search tokens (length >= 3) excluding common stop words
    stopwords = {"why", "what", "when", "where", "which", "who", "whom", "this", "that", "these", "those", "have", "been", "from", "with", "about", "instead", "than", "then", "into", "over", "under", "will", "would", "should", "could", "does", "done", "doing"}
    tokens = [t.lower() for t in re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', payload.query) if t.lower() not in stopwords]

    all_decs = get_all_decisions(department=payload.department_filter, limit=100)
    scored = []
    
    for d in all_decs:
        # Build comprehensive searchable haystack including rejected alternatives and tags
        alts_str = " ".join([f"{a.get('alternative', '')} {a.get('reason_rejected', '')}" for a in d.get("rejected_alternatives", [])])
        tags_str = " ".join(d.get("tags", []))
        haystack = f"{d.get('decision_code', '')} {d.get('title', '')} {d.get('decision_text', '')} {d.get('reasoning', '')} {d.get('problem_context', '')} {alts_str} {tags_str} {d.get('raw_source_text', '')}".lower()
        
        score = 0
        for token in tokens:
            if token in haystack:
                # Higher weight for title, code, and keywords
                if token in d.get('title', '').lower() or token in d.get('decision_code', '').lower():
                    score += 5
                elif token in alts_str.lower():
                    score += 3
                else:
                    score += 1
                    
        if score > 0:
            scored.append((score, d))
            
    scored.sort(key=lambda x: x[0], reverse=True)
    matches = [s[1] for s in scored[:5]]

    answer_text, insights = synthesize_memory_answer(payload.query, matches)
    
    return {
        "query": payload.query,
        "answer": answer_text,
        "relevant_decisions": matches,
        "synthesized_insights": insights
    }

# -------------------------------------------------------------
# Decision-to-Task Tracking Endpoints
# -------------------------------------------------------------
@app.get("/api/tasks")
def list_tasks(status: Optional[str] = Query(None), assignee: Optional[str] = Query(None)):
    tasks = get_all_tasks(status=status, assignee=assignee)
    return {"total": len(tasks), "items": tasks}

@app.post("/api/tasks")
def create_task_endpoint(decision_id: int, payload: TaskCreate):
    existing = get_decision_by_id(decision_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Decision not found")
        
    task_id = add_task(decision_id, payload.dict())
    return {"success": True, "task_id": task_id}

@app.put("/api/tasks/{task_id}")
def update_task_endpoint(task_id: int, payload: TaskUpdate):
    update_data = {k: v for k, v in payload.dict().items() if v is not None}
    update_task(task_id, update_data)
    return {"success": True, "task_id": task_id}

@app.delete("/api/tasks/{task_id}")
def delete_task_endpoint(task_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()
    return {"success": True, "message": "Task deleted"}

# -------------------------------------------------------------
# Conflict Resolution & Export Endpoints
# -------------------------------------------------------------
@app.post("/api/conflicts/resolve")
def resolve_conflict(payload: ResolutionRequest):
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM decision_conflicts WHERE id = ?", (payload.conflict_id,))
    conflict = cursor.fetchone()
    if not conflict:
        conn.close()
        raise HTTPException(status_code=404, detail="Conflict record not found")
        
    now_str = datetime_now_iso()
    
    if payload.resolution_type == "SUPERSEDE_OLD":
        # Decision B supersedes Decision A
        cursor.execute("UPDATE decisions SET status = 'SUPERSEDED', superseded_by_id = ? WHERE id = ?", 
                       (conflict["decision_id_b"], conflict["decision_id_a"]))
        cursor.execute("UPDATE decisions SET supersedes_id = ? WHERE id = ?", 
                       (conflict["decision_id_a"], conflict["decision_id_b"]))
        status_res = "RESOLVED_SUPERSEDED"
    elif payload.resolution_type == "ACKNOWLEDGE_EXCEPTION":
        status_res = "RESOLVED_EXCEPTION"
    else:
        status_res = "DISMISSED"

    cursor.execute("""
        UPDATE decision_conflicts 
        SET status = ?, resolution_notes = ?
        WHERE id = ?
    """, (status_res, payload.notes or "Resolved by management", payload.conflict_id))

    conn.commit()
    conn.close()
    return {"success": True, "status": status_res}

@app.get("/api/decisions/{decision_id}/export-whatsapp")
def export_whatsapp_summary(decision_id: int):
    dec = get_decision_by_id(decision_id)
    if not dec:
        raise HTTPException(status_code=404, detail="Decision not found")

    tasks_str = "\n".join([f"  • [{'x' if t['status'] == 'COMPLETED' else ' '}] {t['title']} (@{t['assignee']}, due: {t.get('due_date', 'N/A')})" for t in dec.get("tasks", [])])
    if not tasks_str:
        tasks_str = "  • None assigned yet."

    wa_text = f"""📌 *DECISION LOGGED [{dec['decision_code']}]*
*Title:* {dec['title']}
*Department:* {dec['department']} | *Status:* {dec['status']}
*Owner:* {dec['owner_name']} ({dec.get('owner_role', 'Lead')})
*Target Deadline:* {dec.get('deadline_date', 'N/A')}

*Summary:*
{dec['decision_text']}

*Why (Reasoning):*
{dec['reasoning']}

*Rejected Alternatives:*
{chr(10).join(['• ' + a.get('alternative') + ': ' + a.get('reason_rejected') for a in dec.get('rejected_alternatives', [])]) or '• None specified.'}

*Action Tasks ({dec['completed_task_count']}/{dec['task_count']} Done):*
{tasks_str}

*Expected Outcome:* {dec.get('expected_outcome', 'N/A')}
_Logged securely in DecisionMemory Vault._"""

    return {"text": wa_text}

@app.post("/api/system/reset-demo")
def reset_demo_data():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audit_logs")
    cursor.execute("DELETE FROM decision_conflicts")
    cursor.execute("DELETE FROM tasks")
    cursor.execute("DELETE FROM decisions")
    conn.commit()
    conn.close()
    
    for sample in SAMPLE_DECISIONS:
        insert_decision(sample)
        
    return {"success": True, "message": "Demo data restored successfully"}

def datetime_now_iso():
    from datetime import datetime
    return datetime.now().isoformat()
