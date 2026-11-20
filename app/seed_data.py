from typing import List, Dict, Any
from app.database import get_decision_count, insert_decision, get_connection

SAMPLE_DECISIONS: List[Dict[str, Any]] = [
    {
        "decision_code": "DEC-2026-001",
        "title": "Migrate Core Cloud Infrastructure from DigitalOcean to AWS (EC2 + RDS)",
        "department": "Engineering",
        "category": "Infrastructure",
        "problem_context": "DigitalOcean experienced 3 unexpected outages during our Diwali flash sale, causing ₹4.8 Lakhs in lost transactions. Traffic is projected to grow 4x in Q1.",
        "decision_text": "Migrate all production backend microservices and PostgreSQL database to AWS using EC2 auto-scaling groups and Multi-AZ RDS PostgreSQL. Enforce IaC with Terraform.",
        "reasoning": "AWS provides robust auto-scaling, managed read-replicas, and SLA-backed uptime. Immediate migration will prevent catastrophic downtime during upcoming high-traffic sale events.",
        "rejected_alternatives": [
            {
                "alternative": "Google Cloud Platform (GCP)",
                "reason_rejected": "DevOps team has zero GCP experience; estimated onboarding and migration was 3-4 weeks longer than AWS."
            },
            {
                "alternative": "Remaining on DigitalOcean with larger Droplets",
                "reason_rejected": "Lacks managed database automated failover and elastic load balancing required for 4x traffic peaks."
            }
        ],
        "owner_name": "Priya Sharma",
        "owner_role": "Lead DevOps Engineer",
        "participants": ["Amit Verma (CTO)", "Priya Sharma (DevOps)", "Rahul Mehta (Lead Backend)"],
        "source_type": "whatsapp",
        "raw_source_text": """[14/10/26, 10:15 AM] Amit Verma: Team, DO crashed again last night. We lost ~4.8L during peak sale. This cannot happen next quarter.
[14/10/26, 10:18 AM] Rahul Mehta: The DB CPU hit 100% and DO droplet throttled IOPS. We need read replicas and auto-scaling immediately.
[14/10/26, 10:22 AM] Priya Sharma: I recommend moving to AWS EC2 + RDS Multi-AZ. We can terraform the entire cluster in 8 days.
[14/10/26, 10:25 AM] Amit Verma: What about GCP? They offered us $5k credits.
[14/10/26, 10:28 AM] Priya Sharma: GCP credits are good, but no one on our team knows GCP IAM or Cloud SQL subtleties. Ramp-up is 3+ weeks. AWS is ready to roll.
[14/10/26, 10:31 AM] Amit Verma: Approved. Let's lock AWS. Priya, you take ownership of the migration. Budget cap is $1,200/mo. Target completion by Nov 28.
[14/10/26, 10:33 AM] Priya Sharma: Understood. Action items: 1) Draft Terraform scripts, 2) Set up RDS replica sync, 3) Schedule 10-min off-peak DNS cutover.""",
        "decision_date": "2026-10-14",
        "deadline_date": "2026-11-28",
        "budget_or_cost": "$1,200/mo cap",
        "status": "IMPLEMENTED",
        "expected_outcome": "Zero downtime during traffic spikes and maintain average API response latency under 120ms at 4x traffic.",
        "outcome_status": "SUCCESS",
        "outcome_notes": "Migration successfully executed on Nov 26 with only 4 minutes of scheduled DNS propagation. Handled Black Friday traffic peak flawlessly with 99.98% uptime. Actual AWS monthly bill was $1,080.",
        "outcome_evaluated_at": "2026-11-29T10:00:00",
        "outcome_evaluated_by": "Amit Verma (CTO)",
        "lessons_learned": "Pre-warming the RDS instances before DNS cutover prevented initial cold-cache spikes. Multi-AZ failover was tested and completed in 24 seconds.",
        "tags": ["engineering", "infrastructure", "aws", "cloud", "devops", "database"],
        "tasks": [
            {
                "title": "Write Terraform modules for AWS VPC, Subnets, and EC2 Auto-scaling",
                "description": "Establish automated reproducible infrastructure as code.",
                "assignee": "Priya Sharma",
                "due_date": "2026-10-25",
                "priority": "HIGH",
                "status": "COMPLETED"
            },
            {
                "title": "Configure Multi-AZ RDS PostgreSQL with read replicas",
                "description": "Enable replication from old DigitalOcean database to AWS RDS.",
                "assignee": "Rahul Mehta",
                "due_date": "2026-11-10",
                "priority": "HIGH",
                "status": "COMPLETED"
            },
            {
                "title": "Execute DNS cutover and verify failover latency",
                "description": "Switch Cloudflare DNS to AWS ALB during 2 AM maintenance window.",
                "assignee": "Priya Sharma",
                "due_date": "2026-11-26",
                "priority": "HIGH",
                "status": "COMPLETED"
            }
        ]
    },
    {
        "decision_code": "DEC-2026-002",
        "title": "Dual Payment Gateway Policy: Razorpay for Domestic INR & Stripe for Global USD/EUR",
        "department": "Finance",
        "category": "Billing & Gateways",
        "problem_context": "Domestic UPI transactions on our previous gateway had an 18% failure rate, while international clients repeatedly reported foreign card declines under RBI 3DS guidelines.",
        "decision_text": "Standardize on a dual payment gateway architecture: Razorpay for all domestic INR transactions (UPI, Netbanking, Rupay) and Stripe for international transactions (USD, EUR, GBP credit/debit cards).",
        "reasoning": "Razorpay provides native UPI auto-routing and 94% success rate in India. Stripe handles global currency conversion and compliance seamlessly without 3DS friction.",
        "rejected_alternatives": [
            {
                "alternative": "Cashfree",
                "reason_rejected": "Slightly cheaper transaction fees (1.75% vs 1.9%) but documentation, SDK updates, and webhook reliability were poor in testing."
            },
            {
                "alternative": "Stripe Exclusively for All Countries",
                "reason_rejected": "Stripe's India UPI integration had high failure rates and required manual approval steps that damaged conversion."
            }
        ],
        "owner_name": "Ananya Sen",
        "owner_role": "Head of Product & Payments",
        "participants": ["Ananya Sen (Product)", "Sanjay Gupta (Finance Controller)", "Vikram Malhotra (COO)"],
        "source_type": "meeting",
        "raw_source_text": """Meeting Notes - Payment Gateway Selection (18 Oct 2026)
Attendees: Ananya Sen, Sanjay Gupta, Vikram Malhotra
Context: 18% UPI drop-offs in tier-2 cities is costing us ₹3L/week. Meanwhile US clients can't pay via cards.
Decision: Dual gateway implementation.
- Domestic INR -> Razorpay exclusively.
- International USD/EUR -> Stripe exclusively.
Rejected: Cashfree (poor SDK), Pure Stripe (fails Indian UPI).
Ownership: Ananya Sen. Target live date: Dec 15.""",
        "decision_date": "2026-10-18",
        "deadline_date": "2026-12-15",
        "budget_or_cost": "Standard gateway fees (1.9% + 2%)",
        "status": "ACTIVE",
        "expected_outcome": "Boost domestic checkout completion from 82% to >93% and achieve 98% international card authorization.",
        "outcome_status": "PENDING_EVALUATION",
        "outcome_notes": "Awaiting end-of-quarter analytics to measure full conversion lift.",
        "tags": ["finance", "payments", "razorpay", "stripe", "billing", "checkout"],
        "tasks": [
            {
                "title": "Implement Razorpay UPI Deep-link SDK on web and mobile checkout",
                "description": "Ensure seamless one-click UPI intent flow.",
                "assignee": "Ananya Sen",
                "due_date": "2026-11-20",
                "priority": "HIGH",
                "status": "COMPLETED"
            },
            {
                "title": "Set up Stripe multi-currency webhooks for recurring subscriptions",
                "description": "Handle USD and EUR recurring invoice generation.",
                "assignee": "Rahul Mehta",
                "due_date": "2026-12-05",
                "priority": "HIGH",
                "status": "IN_PROGRESS"
            },
            {
                "title": "Configure Geo-IP routing at checkout to auto-switch gateways",
                "description": "Route Indian IPs to Razorpay and International IPs to Stripe.",
                "assignee": "Ananya Sen",
                "due_date": "2026-12-12",
                "priority": "MEDIUM",
                "status": "PENDING"
            }
        ]
    },
    {
        "decision_code": "DEC-2026-003",
        "title": "Transition to 100% Remote-First Workplace Policy & Bangalore Office Downsizing",
        "department": "HR",
        "category": "Workplace Policy",
        "problem_context": "Our 3-year commercial office lease in Indiranagar, Bangalore was up for renewal at ₹4.2 Lakhs/month. Team surveys showed 85% preferred remote flexibility.",
        "decision_text": "Adopt an official permanent Remote-First policy for all current and future employees. Non-renewal of Bangalore commercial lease; replace with on-demand WeWork desks for voluntary meetups.",
        "reasoning": "Saves ₹3.5 Lakhs/month net overhead. Expands recruitment reach to senior engineers across Tier-1 and Tier-2 Indian cities without relocation packages.",
        "rejected_alternatives": [
            {
                "alternative": "Mandatory 3-day Hybrid In-Office Attendance",
                "reason_rejected": "Two principal backend engineers gave verbal notice when hybrid mandate was piloted; daily 2-hour Bangalore commute caused burnout."
            },
            {
                "alternative": "Relocating to cheaper suburban office in Whitefield",
                "reason_rejected": "Still required large security deposit and multi-year lease commitment without solving commute friction."
            }
        ],
        "owner_name": "Vikram Malhotra",
        "owner_role": "Chief Operating Officer (COO)",
        "participants": ["Vikram Malhotra (COO)", "Neha Tandon (HR Lead)", "Amit Verma (CTO)"],
        "source_type": "whatsapp",
        "raw_source_text": """[02/09/26, 4:10 PM] Vikram Malhotra: Landlord is asking for 15% rent hike on the Indiranagar office. That's 4.2L/mo.
[02/09/26, 4:14 PM] Neha Tandon: Only 6 out of 28 people come to the office regularly. The rest are in Pune, Delhi, or working from home.
[02/09/26, 4:18 PM] Amit Verma: If we mandate office attendance, Rahul and Priya will leave. We've hired 4 great devs from outside Bangalore who won't relocate.
[02/09/26, 4:22 PM] Vikram Malhotra: Decision: We go 100% remote-first permanently. No mandatory office attendance. We take 6 flexi-passes at WeWork for client meetings.
[02/09/26, 4:25 PM] Neha Tandon: Approved. I'll publish the Remote Work Handbook and home office setup reimbursement policy (₹25,000 one-time).""",
        "decision_date": "2026-09-02",
        "deadline_date": "2026-09-30",
        "budget_or_cost": "₹25,000 WFH setup allowance/employee",
        "status": "ACTIVE",
        "expected_outcome": "Reduce operational facility cost by 75% and maintain voluntary employee turnover below 8% annually.",
        "outcome_status": "SUCCESS",
        "outcome_notes": "Office vacated on Sept 30. Monthly overhead decreased by ₹3.8 Lakhs. Hiring velocity improved from 45 days to 18 days by hiring pan-India. Employee retention at 96%.",
        "outcome_evaluated_at": "2026-11-01T14:30:00",
        "outcome_evaluated_by": "Vikram Malhotra (COO)",
        "lessons_learned": "Holding quarterly in-person team retreats is essential to maintain team bonding and psychological safety in a remote setup.",
        "tags": ["hr", "workplace", "remote-work", "cost-saving", "culture", "talent"],
        "tasks": [
            {
                "title": "Publish Remote Work Handbook and WFH Stipend Guidelines",
                "description": "Establish clear working hours, async communication norms, and equipment reimbursement.",
                "assignee": "Neha Tandon",
                "due_date": "2026-09-15",
                "priority": "HIGH",
                "status": "COMPLETED"
            },
            {
                "title": "Serve lease non-renewal notice to Indiranagar landlord",
                "description": "Initiate security deposit recovery (₹18 Lakhs).",
                "assignee": "Vikram Malhotra",
                "due_date": "2026-09-10",
                "priority": "HIGH",
                "status": "COMPLETED"
            }
        ]
    },
    {
        "decision_code": "DEC-2026-004",
        "title": "Cap Sales Team Discount Authority at 15% Maximum Without Written CEO Approval",
        "department": "Sales",
        "category": "Pricing & Commercial",
        "problem_context": "Sales reps were frequently offering 25% to 35% discounts in end-of-month panic to meet quarterly quota targets, eroding gross profit margins from 64% down to 48%.",
        "decision_text": "Enforce a strict discount ceiling: Account Executives can offer up to 10% discount; Sales VP can approve up to 15%. Any discount exceeding 15% strictly requires written sign-off from the CEO.",
        "reasoning": "Protects unit economics and customer price perception. Eliminates uncoordinated bargaining that trained enterprise buyers to delay purchases until month-end.",
        "rejected_alternatives": [
            {
                "alternative": "Clawback sales rep commissions proportionally on discounted deals",
                "reason_rejected": "Sales team pushback was intense; would have disincentivized closing complex high-volume multi-year deals."
            },
            {
                "alternative": "Zero-discount policy across all customer segments",
                "reason_rejected": "Unrealistic in B2B enterprise SaaS where enterprise buyers mandate formal procurement concession buffers."
            }
        ],
        "owner_name": "Rohan Kapoor",
        "owner_role": "VP of Sales",
        "participants": ["Rohan Kapoor (VP Sales)", "Vikram Malhotra (COO)", "Kunal Shah (CEO)"],
        "source_type": "meeting",
        "raw_source_text": """Executive Sales Committee (25 Sept 2026)
Topic: Gross Margin Dilution due to Uncontrolled Discounting.
Rohan Kapoor presented Q3 numbers: Gross margin fell to 48% because reps offered up to 35% off.
Kunal Shah (CEO): "We are subsidizing enterprise buyers from our own margin. Effective Oct 1, cap is 15%. Anything above 15% needs my explicit approval."
Decision approved. Rohan to configure discount guardrails in HubSpot CRM.""",
        "decision_date": "2026-09-25",
        "deadline_date": "2026-10-15",
        "budget_or_cost": "N/A",
        "status": "ACTIVE",
        "expected_outcome": "Restore gross product margins to >60% while maintaining deal close rates within 10% of baseline.",
        "outcome_status": "PARTIAL_SUCCESS",
        "outcome_notes": "Gross margins successfully rebounded to 58%. However, two major enterprise banking deals worth ₹24 Lakhs stalled because CEO approval took 5 business days during travel.",
        "outcome_evaluated_at": "2026-11-15T16:00:00",
        "outcome_evaluated_by": "Rohan Kapoor (VP Sales)",
        "lessons_learned": "Need a backup approver (COO or VP Sales) with delegated 20% authority when CEO is traveling to avoid deal stagnation.",
        "tags": ["sales", "pricing", "discount-policy", "margin", "commercial"],
        "tasks": [
            {
                "title": "Configure HubSpot Deal Stage Validation Rules for Discounts >15%",
                "description": "Block deal stage advancement if discount field exceeds 15% without attached approval token.",
                "assignee": "Rohan Kapoor",
                "due_date": "2026-10-05",
                "priority": "HIGH",
                "status": "COMPLETED"
            },
            {
                "title": "Implement Mobile Fast-Track Approval Workflow for CEO",
                "description": "Setup Slack/WhatsApp 1-click webhook for high-value deal exceptions.",
                "assignee": "Rohan Kapoor",
                "due_date": "2026-11-25",
                "priority": "MEDIUM",
                "status": "PENDING"
            }
        ]
    },
    {
        "decision_code": "DEC-2026-005",
        "title": "Migrate Customer Support from Shared Gmail to Zendesk with WhatsApp Business API",
        "department": "Operations",
        "category": "Customer Support & Tooling",
        "problem_context": "Customer inquiries were handled through support@company.com in shared Gmail. During the October festival sale, 34 tickets were lost, average first response time was 48 hours, and CSAT plunged to 3.1.",
        "decision_text": "Migrate all customer support operations to Zendesk Suite Team plan, integrated directly with the WhatsApp Business API for multi-agent ticketing.",
        "reasoning": "Provides shared ticket collision detection, automated SLA timers, customer order history lookups, and multi-agent WhatsApp conversation assignment.",
        "rejected_alternatives": [
            {
                "alternative": "Freshdesk",
                "reason_rejected": "Freshdesk was slightly cheaper, but lacked native high-speed WhatsApp webhook stability and Shopify/CRM order embed."
            },
            {
                "alternative": "Intercom",
                "reason_rejected": "Base tier pricing at $800/mo was 3x higher than Zendesk and excessive for current SMB query volumes."
            }
        ],
        "owner_name": "Sneha Patel",
        "owner_role": "Customer Success Lead",
        "participants": ["Sneha Patel (CS Lead)", "Amit Verma (CTO)", "Vikram Malhotra (COO)"],
        "source_type": "whatsapp",
        "raw_source_text": """[05/10/26, 11:00 AM] Sneha Patel: Team, Gmail is completely falling apart for support. Two reps replied to the same customer with contradictory refund info, and 30+ emails were marked read by accident.
[05/10/26, 11:05 AM] Vikram Malhotra: We need a real ticketing system with SLAs and WhatsApp integration. What's the cost of Zendesk?
[05/10/26, 11:08 AM] Sneha Patel: $49/agent/month for 5 agents = $245/mo. We can connect WhatsApp Business directly.
[05/10/26, 11:12 AM] Vikram Malhotra: Go ahead. Sneha to lead. Have it live before Nov 1.""",
        "decision_date": "2026-10-05",
        "deadline_date": "2026-11-01",
        "budget_or_cost": "$245/month",
        "status": "IMPLEMENTED",
        "expected_outcome": "Reduce median first response time to <1 hour and elevate CSAT rating above 4.5/5.0.",
        "outcome_status": "SUCCESS",
        "outcome_notes": "First response time dropped from 48 hours to 34 minutes. Zero lost customer tickets during November. CSAT rose to 4.75 stars across 450 verified ratings.",
        "outcome_evaluated_at": "2026-11-18T11:00:00",
        "outcome_evaluated_by": "Sneha Patel (CS Lead)",
        "lessons_learned": "WhatsApp canned responses for tracking links solved 40% of queries automatically without human agent intervention.",
        "tags": ["operations", "customer-support", "zendesk", "whatsapp", "sla", "csat"],
        "tasks": [
            {
                "title": "Zendesk instance setup and WhatsApp Business API number onboarding",
                "description": "Port support phone number to Meta WhatsApp Business Cloud API.",
                "assignee": "Sneha Patel",
                "due_date": "2026-10-15",
                "priority": "HIGH",
                "status": "COMPLETED"
            },
            {
                "title": "Create SLA notification triggers and routing macros",
                "description": "Trigger manager alert if high-priority ticket is unassigned for >15 mins.",
                "assignee": "Sneha Patel",
                "due_date": "2026-10-22",
                "priority": "HIGH",
                "status": "COMPLETED"
            },
            {
                "title": "Train 4 customer support reps on ticket states and tagging",
                "description": "Standardize tag taxonomy for refunds, logistics, and tech bugs.",
                "assignee": "Sneha Patel",
                "due_date": "2026-10-28",
                "priority": "MEDIUM",
                "status": "COMPLETED"
            }
        ]
    }
]

def seed_sample_data():
    count = get_decision_count()
    if count == 0:
        print("[DecisionMemory] Seeding initial realistic decisions and historical memory...")
        for sample in SAMPLE_DECISIONS:
            insert_decision(sample)
        print(f"[DecisionMemory] Successfully seeded {len(SAMPLE_DECISIONS)} decisions with tasks and context.")
    else:
        print(f"[DecisionMemory] Database already contains {count} decisions. Skipping seeding.")
