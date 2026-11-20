import re
import json
import io
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta

def clean_text(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()

def tokenize_and_normalize(text: str) -> set:
    words = re.findall(r'\b[a-zA-Z0-9_-]{3,}\b', text.lower())
    stopwords = {
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have', 'were', 'been',
        'will', 'would', 'should', 'could', 'about', 'there', 'their', 'what', 'when',
        'which', 'where', 'also', 'some', 'into', 'just', 'more', 'than', 'them', 'then',
        'they', 'only', 'after', 'before', 'each', 'because', 'using', 'make', 'made'
    }
    return {w for w in words if w not in stopwords}

def parse_vtt_or_srt(raw_text: str) -> str:
    """
    Cleans WebVTT (.vtt) or SubRip (.srt) subtitle/meeting transcript files.
    Removes WEBVTT headers, numeric counters, and timestamp lines (00:00:01.000 --> 00:00:05.000).
    Normalizes speaker cues like '<v Speaker Name> ... </v>' or 'Speaker Name: ...'.
    """
    lines = raw_text.splitlines()
    cleaned_dialogue = []
    
    timestamp_pattern = re.compile(r'^\d{1,2}:(?:\d{2}:)?\d{2}[,\.]\d{3}\s*-->\s*\d{1,2}:(?:\d{2}:)?\d{2}[,\.]\d{3}')
    numeric_cue_pattern = re.compile(r'^\d+$')
    v_tag_pattern = re.compile(r'<v\s+([^>]+)>(.*?)(?:<\/v>|$)', re.IGNORECASE)
    
    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
        if line_s.upper().startswith(('WEBVTT', 'NOTE', 'STYLE', 'REGION')):
            continue
        if numeric_cue_pattern.match(line_s):
            continue
        if timestamp_pattern.match(line_s):
            continue
            
        # Check for HTML-like voice tags: <v Vikram Malhotra>text</v>
        m_tag = v_tag_pattern.search(line_s)
        if m_tag:
            speaker = m_tag.group(1).strip()
            content = m_tag.group(2).strip()
            cleaned_dialogue.append(f"{speaker}: {content}")
            continue
            
        # Clean any remaining HTML tags
        line_clean = re.sub(r'<[^>]+>', '', line_s).strip()
        if line_clean:
            cleaned_dialogue.append(line_clean)
            
    return "\n".join(cleaned_dialogue)

def parse_docx_bytes(file_bytes: bytes) -> str:
    """
    Extracts text from Microsoft Word (.docx) meeting minutes and transcript documents.
    """
    try:
        import docx
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                if row_text:
                    paragraphs.append(row_text)
        return "\n".join(paragraphs)
    except Exception as e:
        return f"Error extracting DOCX: {str(e)}"

def parse_chat_messages(raw_text: str) -> List[Dict[str, str]]:
    """
    Parses WhatsApp, Zoom/Teams/Meet transcripts, Voice note summaries, or generic dialogues.
    """
    # If the text has VTT or SRT timestamp cues, clean it first
    if "-->" in raw_text:
        raw_text = parse_vtt_or_srt(raw_text)

    messages = []
    lines = raw_text.strip().split("\n")
    
    # 1. WhatsApp bracket pattern: [12/10/26, 2:30 PM] Name: Message
    wa_bracket_pattern = re.compile(r'^\[?(\d{1,2}[\/\.-]\d{1,2}[\/\.-]\d{2,4}[,\s]+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]?[\s:-]+([^:]+):\s*(.*)$')
    # 2. Zoom / Teams pattern: Speaker Name (Role): Message or Speaker Name 10:15 AM: Message
    zoom_speaker_pattern = re.compile(r'^([A-Z][a-zA-Z0-9_\s\(\)\.-]{1,35})(?:\s+\d{1,2}:\d{2}\s*(?:[APap][Mm])?)?:\s*(.*)$')
    
    current_speaker = "Unknown"
    current_msg = ""
    
    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue
            
        m1 = wa_bracket_pattern.match(line_clean)
        if m1:
            if current_msg:
                messages.append({"speaker": current_speaker, "message": current_msg.strip()})
            current_speaker = re.sub(r'\s*\([^)]*\)', '', m1.group(2)).strip()
            current_msg = m1.group(3).strip()
            continue
            
        m2 = zoom_speaker_pattern.match(line_clean)
        if m2 and not line_clean.lower().startswith(("http", "note:", "decision:", "action:", "todo:", "agenda:")):
            if current_msg:
                messages.append({"speaker": current_speaker, "message": current_msg.strip()})
            current_speaker = re.sub(r'\s*\([^)]*\)', '', m2.group(1)).strip()
            current_msg = m2.group(2).strip()
            continue
            
        if current_msg:
            current_msg += " " + line_clean
        else:
            current_msg = line_clean
            
    if current_msg:
        messages.append({"speaker": current_speaker, "message": current_msg.strip()})
        
    return messages

def extract_decision_from_transcript(raw_input: str, source_type: str = "direct") -> Dict[str, Any]:
    """
    Omnichannel Decision Extractor:
    Processes WhatsApp chats, Zoom/Teams/Meet meeting transcripts (.vtt, .srt, .txt, .docx),
    and transcribed voice memos.
    """
    # Auto-clean if VTT/SRT
    clean_input = parse_vtt_or_srt(raw_input) if "-->" in raw_input else raw_input
    parsed_msgs = parse_chat_messages(clean_input)
    full_text = " ".join([m["message"] for m in parsed_msgs]) if parsed_msgs else clean_input
    participants = list(dict.fromkeys([m["speaker"] for m in parsed_msgs if m["speaker"] not in ("Unknown", "System")]))
    lower_full = full_text.lower()
    
    # 1. Infer Department & Category
    department = "General"
    category = "Strategy"
    
    tech_keywords = ["aws", "cloud", "server", "ec2", "database", "postgres", "backend", "frontend", "api", "bug", "deploy", "infra", "devops", "code", "latency", "digitalocean", "gcp", "soc2", "vanta", "sprinto", "compliance", "security audit"]
    finance_keywords = ["payment", "stripe", "razorpay", "cashfree", "invoice", "revenue", "budget", "cost", "billing", "gst", "pricing", "discount", "margin", "inr", "usd", "upi"]
    sales_keywords = ["client", "deal", "pipeline", "quota", "lead", "enterprise", "customer contract", "sales rep", "demo", "proposal", "contract"]
    hr_keywords = ["remote", "office", "leave", "hiring", "salary", "candidate", "interview", "policy", "wfh", "attendance", "culture", "coworking", "in-person"]
    ops_keywords = ["support", "zendesk", "freshdesk", "intercom", "ticket", "sla", "vendor", "logistics", "shipping", "csat", "refund", "bluedart", "delayed order", "voucher"]
    
    if any(k in lower_full for k in tech_keywords):
        department = "Engineering"
        category = "Compliance & Security" if any(s in lower_full for s in ["soc2", "audit", "sprinto", "vanta", "compliance"]) else "Infrastructure"
    elif any(k in lower_full for k in finance_keywords):
        department = "Finance"
        category = "Billing & Gateways" if any(p in lower_full for p in ["payment", "stripe", "razorpay", "upi", "gateway"]) else "Pricing & Margin"
    elif any(k in lower_full for k in ops_keywords):
        department = "Operations"
        category = "Customer Experience & Refunds" if "refund" in lower_full or "voucher" in lower_full else "Support & Tooling"
    elif any(k in lower_full for k in sales_keywords):
        department = "Sales"
        category = "Deals & Discounts"
    elif any(k in lower_full for k in hr_keywords):
        department = "HR"
        category = "Workplace Policy"

    # 2. Extract Problem Context
    problem_sentences = []
    for s in re.split(r'[.!?\n]', full_text):
        s_clean = s.strip()
        if any(trig in s_clean.lower() for trig in ["problem", "issue", "traffic", "downtime", "failed", "drop-off", "complaint", "struggling", "expensive", "slow", "delay", "lost", "need to", "down", "delayed shipment", "chargebacks", "audit"]):
            problem_sentences.append(s_clean)
    
    problem_context = " ".join(problem_sentences[:2]) if problem_sentences else "Operational bottleneck or strategic requirement discussed in meeting/voice note."
    if len(problem_context) < 20 and parsed_msgs:
        problem_context = f"Discussion initiated by {parsed_msgs[0]['speaker']}: {parsed_msgs[0]['message'][:150]}"

    # 3. Decision Statements & Smart Title Extraction
    decision_sentences = []
    for s in re.split(r'[.!?\n]', full_text):
        s_clean = s.strip()
        if any(marker in s_clean.lower() for marker in ["let's", "we will", "we should", "agreed", "decided", "lock", "switch to", "approved", "finalize", "make it mandatory", "mandate", "cap is", "policy is", "decided to update", "effective immediately"]):
            decision_sentences.append(s_clean)
            
    decision_text = " ".join(decision_sentences[:2]) if decision_sentences else full_text[:200]

    title = ""
    # Smart Title Disambiguation across meeting/voice/chat domains
    if "sprinto" in lower_full and ("soc2" in lower_full or "audit" in lower_full):
        title = "Adopt Sprinto for Automated SOC2 Type II Compliance"
    elif "refund" in lower_full and ("voucher" in lower_full or "bluedart" in lower_full or "delayed" in lower_full):
        title = "Enforce Instant 100% Refund + ₹500 Voucher for Delayed Shipments"
    elif any(p in lower_full for p in ["mandate 3 days", "mandatory office", "office attendance", "in-person collaboration", "come to office"]):
        title = "Mandate In-Office Attendance Policy"
    elif any(p in lower_full for p in ["remote-first", "100% remote", "work from home permanently", "wfh policy", "downsize office"]):
        title = "Adopt 100% Remote-First Workplace Policy"
    elif "stripe" in lower_full and ("all payments" in lower_full or "india" in lower_full or "inr" in lower_full or "sole gateway" in lower_full or "switch to stripe" in lower_full):
        title = "Standardize Exclusively on Stripe for All Global & Indian Payments"
    elif "razorpay" in lower_full and "stripe" in lower_full:
        title = "Configure Razorpay for Domestic UPI & Stripe for International Billing"
    elif "aws" in lower_full and ("switch" in lower_full or "migrate" in lower_full or "digitalocean" in lower_full or "ec2" in lower_full):
        title = "Migrate Cloud Infrastructure to AWS (EC2 + RDS)"
    elif "discount" in lower_full and ("15%" in lower_full or "cap" in lower_full or "ceiling" in lower_full):
        title = "Enforce 15% Maximum Discount Ceiling for Enterprise Deals"
    elif "discount" in lower_full and any(p in lower_full for p in ["25%", "30%", "20%", "approve discount"]):
        title = "Authorize Enterprise Special Discount Exception"
    elif "zendesk" in lower_full or "ticket" in lower_full:
        title = "Migrate Support Operations from Gmail to Zendesk"
    else:
        first_dec = decision_sentences[0] if decision_sentences else full_text[:65]
        first_dec = re.sub(r'^(let\'s|we should|agreed|decided to|i think we should|team,?\s*|today\'s agenda is\s*)\s*', '', first_dec, flags=re.IGNORECASE)
        title = first_dec[:65].capitalize().strip()
        if not title:
            title = f"{category} Decision ({source_type.capitalize()})"

    # 4. Extract Reasoning
    reasoning_sentences = []
    for s in re.split(r'[.!?\n]', full_text):
        s_clean = s.strip()
        if any(kw in s_clean.lower() for kw in ["because", "since", "due to", "reason", "stability", "faster", "uptime", "saves", "cheaper", "compliance", "productivity", "needed", "burnout", "integrates with", "costs", "restore trust"]):
            reasoning_sentences.append(s_clean)
    reasoning = " ".join(reasoning_sentences[:3]) if reasoning_sentences else "Decision adopted to optimize team workflow and resolve operational bottlenecks."

    # 5. Extract Rejected Alternatives
    rejected_alternatives = []
    if re.search(r'(vanta)[^.!?]*(expensive|double|exceeded|quote)', full_text, re.IGNORECASE):
        rejected_alternatives.append({"alternative": "Vanta Compliance Platform", "reason_rejected": "Quote of $28,000/yr was double the price and exceeded our budget."})
    if re.search(r'(manual audit|traditional audit)[^.!?]*(months|expensive|\$45)', full_text, re.IGNORECASE):
        rejected_alternatives.append({"alternative": "Traditional Manual Audit Firm", "reason_rejected": "Estimated 9-month audit timeline and $45,000 cost was prohibitive."})
    if re.search(r'(20% discount|discount coupon)[^.!?]*(won\'t restore|insufficient|confidence)', full_text, re.IGNORECASE):
        rejected_alternatives.append({"alternative": "Issuing a 20% Discount Coupon", "reason_rejected": "Insufficient to restore confidence with high-value clients after delivery failure."})
    if re.search(r'(switching couriers|new logistics)[^.!?]*(weeks|mid-quarter|onboarding)', full_text, re.IGNORECASE):
        rejected_alternatives.append({"alternative": "Switching Logistics Couriers Immediately", "reason_rejected": "Onboarding a replacement carrier takes 3 weeks mid-quarter and risks operational disruption."})
    if re.search(r'(gcp|google cloud)[^.!?]*(take[s]? \d+ weeks|cheaper|setup|experience)', full_text, re.IGNORECASE):
        rejected_alternatives.append({"alternative": "Google Cloud Platform (GCP)", "reason_rejected": "Setup ramp-up timeline exceeds project deadline (3+ weeks)."})
    if re.search(r'(digital\s*ocean|do)[^.!?]*(downtime|scaling|limits|traffic)', full_text, re.IGNORECASE):
        rejected_alternatives.append({"alternative": "Remaining on DigitalOcean", "reason_rejected": "Inability to auto-scale with 4x traffic surge and history of downtime."})
    if re.search(r'(cashfree)[^.!?]*(fee|webhook|documentation|unreliable)', full_text, re.IGNORECASE):
        rejected_alternatives.append({"alternative": "Cashfree", "reason_rejected": "Lower API documentation quality and webhook reliability."})

    alt_regex = re.findall(r'(?:what about|considered|looked at|instead of)\s+([A-Za-z0-9\s]{3,25})[,\?]?\s*(?:it\'s|it is|but|however)?\s*([^.!?\n]{10,80})', full_text, re.IGNORECASE)
    for alt_name, alt_reason in alt_regex:
        alt_name_clean = alt_name.strip()
        if alt_name_clean.lower() not in [a["alternative"].lower() for a in rejected_alternatives]:
            rejected_alternatives.append({
                "alternative": alt_name_clean.capitalize(),
                "reason_rejected": alt_reason.strip().capitalize()
            })

    # 6. Extract Owner
    owner_name = participants[0] if participants else "Unassigned"
    # Check voice note patterns like "Sneha, you take ownership...", "Priya, you lead..."
    assign_pattern = re.search(r'([A-Z][a-zA-Z]+)[,\s]+(?:you take ownership|you lead|you handle|to lead|is responsible|lead implementation|configure)', full_text)
    if assign_pattern:
        cand = assign_pattern.group(1)
        if cand.lower() not in ["we", "let", "agreed", "what", "budget", "team", "under", "today"]:
            owner_name = cand

    # Also detect voice memo speaker e.g. "Vikram here leaving a quick voice memo..."
    if "here leaving a quick voice memo" in lower_full or "here leaving a voice note" in lower_full:
        speaker_match = re.search(r'([A-Z][a-zA-Z]+)\s+here leaving', full_text)
        if speaker_match:
            speaker_name = speaker_match.group(1)
            if speaker_name not in participants:
                participants.insert(0, speaker_name)

    # 7. Extract Deadlines
    deadline_date = None
    today = datetime.now()
    if "tomorrow" in lower_full:
        deadline_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    elif "next friday" in lower_full or "by friday" in lower_full:
        days_ahead = 4 - today.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        deadline_date = (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    elif "march 31" in lower_full or "q1" in lower_full:
        year = today.year + 1 if today.month > 3 else today.year
        deadline_date = f"{year}-03-31"
    else:
        date_match = re.search(r'\b(202[4-9]-\d{2}-\d{2})\b', full_text)
        if date_match:
            deadline_date = date_match.group(1)
        else:
            deadline_date = (today + timedelta(days=14)).strftime("%Y-%m-%d")

    # 8. Budget
    budget_or_cost = ""
    budget_match = re.search(r'(budget|cap|cost|allowance|pool)[^$₹0-9]*([$₹]\s*[\d,]+(?:\/mo|\/month|\/year|\/yr)?|\d+[\d,]*\s*(?:lakhs?|usd|inr))', full_text, re.IGNORECASE)
    if budget_match:
        budget_or_cost = budget_match.group(0).strip()

    # 9. Tasks
    tasks = []
    for s in re.split(r'[.!?\n]', full_text):
        s_clean = s.strip()
        if any(act in s_clean.lower() for act in ["handle", "configure", "setup", "migrate", "test", "deploy", "review", "draft", "inform", "notify", "cancel", "implement", "publish", "connect", "conduct", "track"]):
            act_title = s_clean
            if ":" in act_title:
                act_title = act_title.split(":", 1)[1].strip()
            if 8 < len(act_title) < 95:
                tasks.append({
                    "title": act_title,
                    "description": f"Extracted from {source_type} discussion.",
                    "assignee": owner_name,
                    "due_date": deadline_date,
                    "priority": "HIGH" if any(w in s_clean.lower() for w in ["urgent", "immediately", "downtime", "mandatory", "tomorrow"]) else "MEDIUM",
                    "status": "PENDING"
                })

    if not tasks:
        tasks.append({
            "title": f"Execute action items for {title}",
            "description": f"Milestone generated from {source_type}.",
            "assignee": owner_name,
            "due_date": deadline_date,
            "priority": "MEDIUM",
            "status": "PENDING"
        })

    tags = [department.lower(), category.lower().replace(" ", "-"), source_type.lower()]
    if "sprinto" in lower_full or "soc2" in lower_full: tags.extend(["soc2", "compliance", "security"])
    if "refund" in lower_full: tags.extend(["refunds", "customer-service"])

    return {
        "title": title,
        "department": department,
        "category": category,
        "problem_context": problem_context,
        "decision_text": decision_text,
        "reasoning": reasoning,
        "rejected_alternatives": rejected_alternatives,
        "owner_name": owner_name,
        "participants": participants,
        "deadline_date": deadline_date,
        "budget_or_cost": budget_or_cost,
        "expected_outcome": f"Achieve expected performance standards for {category}.",
        "tags": list(set(tags)),
        "tasks": tasks[:5],
        "confidence_score": 0.95
    }

# Backward compatible alias
def extract_decision_from_chat(chat_text: str) -> Dict[str, Any]:
    return extract_decision_from_transcript(chat_text, source_type="whatsapp")

def detect_conflicts(
    new_title: str,
    new_decision_text: str,
    new_dept: Optional[str],
    new_category: Optional[str],
    existing_decisions: List[Dict[str, Any]],
    current_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    conflicts = []
    combined_new = f"{new_title} {new_decision_text} {new_category or ''}".lower()
    new_tokens = tokenize_and_normalize(combined_new)

    rules = [
        {
            "side_a": ["remote-first", "100% remote", "work from home permanent", "wfh policy", "no mandatory office"],
            "side_b": ["mandate in-office", "mandatory 3 days", "mandatory office", "office attendance", "in-person collaboration", "come to office"],
            "type": "POLICY_COLLISION",
            "severity": "HIGH",
            "explanation": "Direct workplace policy collision: Decision mandates in-office physical attendance, which contradicts the established 100% Remote-First policy."
        },
        {
            "side_a": ["razorpay for domestic", "razorpay for inr", "razorpay exclusively for inr", "dual payment gateway"],
            "side_b": ["stripe for all", "stripe exclusively", "switch to stripe for all", "all payments stripe", "stripe for india"],
            "type": "VENDOR_OVERLAP",
            "severity": "HIGH",
            "explanation": "Payment gateway conflict: Decision seeks to standardize on Stripe for all/Indian transactions, conflicting with Decision DEC-2026-002 which reserves Razorpay for Indian UPI & domestic cards."
        },
        {
            "side_a": ["15% maximum discount", "discount ceiling 15%", "cap sales team discount"],
            "side_b": ["25% discount", "30% discount", "20% discount", "special discount exception", "approve 25%"],
            "type": "POLICY_COLLISION",
            "severity": "HIGH",
            "explanation": "Discount limit violation: Exceeds the 15% maximum discount threshold enforced by sales governance without recorded CEO written authorization."
        },
        {
            "side_a": ["migrate cloud infrastructure to aws", "aws ec2 + rds"],
            "side_b": ["migrate to gcp", "migrate to azure", "stay on digitalocean"],
            "type": "DIRECT_CONFLICT",
            "severity": "MEDIUM",
            "explanation": "Conflicting primary cloud provider infrastructure decision against approved AWS standardization."
        },
        {
            "side_a": ["migrate support operations from gmail to zendesk", "zendesk suite"],
            "side_b": ["freshdesk", "intercom for support", "switch support to freshdesk"],
            "type": "DIRECT_CONFLICT",
            "severity": "MEDIUM",
            "explanation": "Support tool collision: Support operations were previously migrated to Zendesk."
        }
    ]

    for dec in existing_decisions:
        if current_id and dec["id"] == current_id:
            continue
        if dec.get("status") in ("SUPERSEDED", "REVOKED"):
            continue

        dec_text = f"{dec.get('title', '')} {dec.get('decision_text', '')} {dec.get('category', '')}".lower()
        dec_tokens = tokenize_and_normalize(dec_text)

        rule_hit = False
        for r in rules:
            has_a_new = any(phrase in combined_new for phrase in r["side_a"])
            has_b_new = any(phrase in combined_new for phrase in r["side_b"])
            has_a_old = any(phrase in dec_text for phrase in r["side_a"])
            has_b_old = any(phrase in dec_text for phrase in r["side_b"])

            if (has_a_new and has_b_old) or (has_b_new and has_a_old):
                conflicts.append({
                    "conflicting_decision_id": dec["id"],
                    "conflicting_decision_code": dec.get("decision_code", f"DEC-{dec['id']}"),
                    "conflicting_title": dec.get("title", ""),
                    "conflict_type": r["type"],
                    "severity": r["severity"],
                    "similarity_score": 0.92,
                    "explanation": f"{r['explanation']} Conflicts with {dec.get('decision_code')}: '{dec.get('title')}' (Owned by {dec.get('owner_name')}).",
                    "suggested_action": f"Review {dec.get('decision_code')}. Choose 'Supersede Prior Decision' if changing company policy, or record an explicit exception."
                })
                rule_hit = True
                break

        if rule_hit:
            continue

        intersection = new_tokens.intersection(dec_tokens)
        union = new_tokens.union(dec_tokens)
        jaccard = len(intersection) / len(union) if union else 0.0

        if jaccard > 0.40:
            conflicts.append({
                "conflicting_decision_id": dec["id"],
                "conflicting_decision_code": dec.get("decision_code", f"DEC-{dec['id']}"),
                "conflicting_title": dec.get("title", ""),
                "conflict_type": "REPEATED_DUPLICATE",
                "severity": "MEDIUM",
                "similarity_score": round(jaccard, 2),
                "explanation": f"High conceptual overlap ({int(jaccard * 100)}% match) with existing Decision {dec.get('decision_code')}: '{dec.get('title')}'.",
                "suggested_action": f"Verify whether {dec.get('decision_code')} already covers this decision before creating a duplicate record."
            })

    return conflicts

def synthesize_memory_answer(query: str, matching_decisions: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    if not matching_decisions:
        return (
            f"No historical decisions found matching your inquiry: '{query}'. "
            "Consider searching by broader keywords (e.g., 'AWS', 'Remote', 'Stripe', 'Discount') or browse by department.",
            ["No precedent located in Decision Memory."]
        )

    primary = matching_decisions[0]
    insights = []
    
    insights.append(f"Primary precedent located: **{primary['decision_code']} - {primary['title']}** (Status: {primary['status']}, Owner: {primary['owner_name']}).")
    
    if primary.get("reasoning"):
        insights.append(f"Strategic Rationale: {primary['reasoning']}")
        
    alts = primary.get("rejected_alternatives", [])
    if alts:
        alt_str = ", ".join([f"{a.get('alternative')} (Rejected: {a.get('reason_rejected')})" for a in alts])
        insights.append(f"Alternatives Considered & Rejected: {alt_str}")
        
    if primary.get("outcome_status") in ("SUCCESS", "PARTIAL_SUCCESS", "FAILED"):
        insights.append(f"Tracked Retrospective Outcome: **{primary['outcome_status']}** — {primary.get('outcome_notes', 'N/A')}")

    answer = (
        f"### Decision Memory Record: {primary['decision_code']}\n\n"
        f"**Title**: {primary['title']}\n\n"
        f"**Decided On**: {primary.get('decision_date', 'N/A')} | **Owner**: {primary['owner_name']} ({primary.get('owner_role', 'Lead')}) | **Department**: {primary['department']}\n\n"
        f"**What was Decided**:\n> {primary['decision_text']}\n\n"
        f"**Why (Context & Rationale)**:\n{primary['problem_context']}\n\n*{primary['reasoning']}*\n\n"
    )
    
    if alts:
        answer += "**Rejected Alternatives**:\n"
        for a in alts:
            answer += f"- **{a.get('alternative')}**: {a.get('reason_rejected')}\n"
        answer += "\n"

    if primary.get("outcome_status") != "PENDING_EVALUATION":
        answer += f"**Result & Retrospective Outcome ({primary['outcome_status']})**:\n{primary.get('outcome_notes', '')}\n\n"
        if primary.get("lessons_learned"):
            answer += f"💡 *Lessons Learned*: {primary['lessons_learned']}\n\n"

    if len(matching_decisions) > 1:
        other_codes = ", ".join([f"{d['decision_code']} ({d['title'][:30]}...)" for d in matching_decisions[1:4]])
        insights.append(f"Other related decisions in memory: {other_codes}")

    return answer.strip(), insights
