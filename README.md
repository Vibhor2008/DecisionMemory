# DecisionMemory — Institutional Decision Memory Platform

> **Creating a searchable, conflict-aware, and outcome-verified record of business decisions for small and growing businesses across WhatsApp chats, Meeting Transcripts, and Voice Notes.**

---

## 📌 Problem Statement

In small and growing businesses, critical decisions are made across **WhatsApp chats, Zoom/Teams calls, phone discussions, and informal voice notes**. 

However:
1. **Lost Rationale & Context**: The *reasons* behind decisions, *why* alternatives were rejected, and the market assumptions made at the time are rarely documented in one place.
2. **Accountability Gaps**: Ownership, explicit deadlines, and follow-up action items slip through the cracks.
3. **Turnover Amnesia**: When employees leave or projects fail, management struggles to reconstruct what was decided earlier, why it was chosen, and what remains pending.
4. **Policy Clashes & Repeated Mistakes**: New managers repeatedly re-invent decisions or introduce contradictory policies without realizing prior precedents exist.

---

## 💡 The Solution: DecisionMemory Omnichannel Decision Intelligence

**DecisionMemory** turns fragmented chat logs, meeting recordings, and voice memos into structured, queryable, and verifiable institutional memory.

### 🌟 Key Capabilities

1. **🎙️ Omnichannel Ingestion (WhatsApp • Meetings • Voice Files)**
   - **WhatsApp Chats**: Import text exports or raw pasted chat threads with multi-speaker detection.
   - **Meeting Transcripts**: Native support for Zoom, Microsoft Teams, Google Meet, and Otter.ai subtitle files (**`.vtt`**, **`.srt`**), Word documents (**`.docx`**), and text minutes (**`.txt`**).
   - **Voice Notes & Audio**: Upload audio files (**`.wav`**, **`.mp3`**, **`.m4a`**, **`.ogg`**, **`.webm`**) or dictate decisions directly into your browser microphone using real-time streaming speech recognition.

2. **🧠 Decision History with Rich Context**
   - Captures the exact problem trigger, rationale ("why"), budget limits, participants, and the raw source transcript as verifiable evidence.
   - Preserves **Rejected Alternatives** (what other vendors or approaches were considered and exactly why they were dropped).

3. **🔍 Searchable Decision Records (Semantic & Filterable)**
   - Instant search across decision titles, reasoning, rejected options, owners, tags, and departments.
   - Filter by status (`ACTIVE`, `IMPLEMENTED`, `SUPERSEDED`, `DRAFT`) and department (`Engineering`, `Finance`, `HR`, `Sales`, `Operations`).

4. **📋 Decision-to-Task Execution Tracking**
   - Automatically links action items to decisions with assignees, due dates, priority, and progress tracking.
   - Visual Kanban board with completion health scores to ensure decisions are actually executed.

5. **⚠️ AI Conflict & Duplication Radar**
   - Automatically detects contradictory decisions (policy clashes, duplicate decisions, vendor overlaps, and discount limit violations) before they cause operational chaos.
   - Recommends clear resolution paths: *Supersede Prior Decision*, *Record Policy Exception*, or *Dismiss*.

6. **🎯 Outcome & Retrospective Loop ("Did It Work?")**
   - Evaluates whether decisions produced their expected KPIs (`SUCCESS`, `PARTIAL_SUCCESS`, `FAILED`).
   - Captures post-mortems and **Lessons Learned** so future leaders don't repeat the same mistakes.

7. **✨ "Ask Decision Memory" AI Q&A**
   - Natural language executive assistant: Ask *"Why did we choose AWS over GCP?"* or *"What is our policy on remote work and office rent?"* and get instant synthesized answers with citations.

8. **📄 WhatsApp Broadcast Exporter**
   - Generates formatted WhatsApp messages with checkmarks and bolding ready to paste back into the group chat.

---

## 🏗️ Architecture

```
c:\Genathon\
├── app\
│   ├── __init__.py
│   ├── main.py              # FastAPI REST endpoints, file upload & static serving
│   ├── database.py          # SQLite schema, WAL mode, queries, migrations (decisionmemory.db)
│   ├── models.py            # Pydantic schemas for decisions, tasks, conflicts
│   ├── nlp_engine.py        # Omnichannel extractor (VTT, DOCX, Voice, Chat), conflicts & Q&A
│   ├── seed_data.py         # Realistic small business decisions & chat history
│   └── static\
│       ├── index.html       # Single-Page UI (Live Mic, File Dropzone, Kanban, Modals)
│       ├── app.js           # Frontend controller, Web Speech API & live API integration
│       └── styles.css       # Custom styling, animations & glowing indicators
├── requirements.txt         # Dependencies (FastAPI, Uvicorn, SpeechRecognition, python-docx, etc.)
├── run.py                   # Automated startup script
└── README.md
```

---

## 🚀 Quickstart Guide

### 1. Requirements
- Python 3.10+ (Tested on Python 3.15)
- Standard browser (Chrome, Edge, Opera GX, Safari, Firefox)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Start the Platform
```bash
python run.py
```
Open your browser at: **`http://127.0.0.1:8000`**

---

## 🧪 Interactive Omnichannel Demos

Inside the **Omnichannel Importer** tab:
1. **💬 WhatsApp Tab**: Select *"1. AWS Migration"* to see WhatsApp chat parsing.
2. **👥 Meeting Transcript Tab**: Select *"2. Zoom Meeting (.vtt): SOC2 & Sprinto"* or upload any `.vtt`, `.srt`, or `.docx` file to see timestamp stripping, agenda parsing, and rejected vendor extraction.
3. **🎙️ Voice Note Tab**: Select *"3. Voice Memo: Urgent Refund Policy"* or click **"Start Recording"** to dictate a decision live using your microphone!
4. **⚠️ Conflict Radar**: Select *"4. Mandate Office"* or *"5. Stripe Exclusivity"* to see real-time AI policy collision alerts.

---

## 🛡️ License
MIT License. Built for small and growing businesses to preserve institutional wisdom.
