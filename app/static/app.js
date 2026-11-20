// DecisionMemory Frontend Application Logic

let currentTab = 'dashboard';
let cachedDecisions = [];
let cachedTasks = [];
let cachedStats = null;
let deptChartInstance = null;
let statusChartInstance = null;
let extractedDecisionCache = null;
let searchDebounceTimer = null;

// Sample Chat, Meeting & Voice Scenarios for Demo & Hackathon testing
const SAMPLE_CHATS = {
    infra: `[14/10/26, 10:15 AM] Amit Verma: Team, DO crashed again last night. We lost ~4.8L during peak sale. This cannot happen next quarter.
[14/10/26, 10:18 AM] Rahul Mehta: The DB CPU hit 100% and DO droplet throttled IOPS. We need read replicas and auto-scaling immediately.
[14/10/26, 10:22 AM] Priya Sharma: I recommend moving to AWS EC2 + RDS Multi-AZ. We can terraform the entire cluster in 8 days.
[14/10/26, 10:25 AM] Amit Verma: What about GCP? They offered us $5k credits.
[14/10/26, 10:28 AM] Priya Sharma: GCP credits are good, but no one on our team knows GCP IAM or Cloud SQL subtleties. Ramp-up is 3+ weeks. AWS is ready to roll.
[14/10/26, 10:31 AM] Amit Verma: Approved. Let's lock AWS. Priya, you take ownership of the migration. Budget cap is $1,200/mo. Target completion by Nov 28.
[14/10/26, 10:33 AM] Priya Sharma: Understood. Action items: 1) Draft Terraform scripts, 2) Set up RDS replica sync, 3) Schedule 10-min off-peak DNS cutover.`,

    meeting_zoom: `WEBVTT

1
00:00:01.200 --> 00:00:06.500
Vikram Malhotra: Good morning everyone. Today's meeting agenda is our enterprise readiness and client security audit requirements.

2
00:00:07.100 --> 00:00:14.300
Ananya Sen: We lost two Fortune 500 enterprise deals last week because we lack SOC2 Type II certification. Enterprise buyers require third-party audit reports.

3
00:00:15.000 --> 00:00:22.400
Amit Verma: A traditional manual audit firm takes 9 months and costs $45,000. Alternatively, we looked at automated compliance platforms Sprinto and Vanta.

4
00:00:23.000 --> 00:00:29.800
Priya Sharma: Sprinto gave us a quote of $14,000/year and integrates directly with our AWS setup. Vanta quoted $28,000.

5
00:00:30.200 --> 00:00:38.500
Amit Verma: Vanta is too expensive for our stage. Let's decide: we lock Sprinto for automated SOC2 Type II compliance by Q1. Priya, you lead implementation.

6
00:00:39.000 --> 00:00:44.200
Vikram Malhotra: Approved. Budget cap is $15,000. Target certification date is March 31.
Priya Sharma: Understood. Action items: connect Sprinto to AWS IAM, draft employee security training policies, and schedule pen testing.`,

    voice_refund: `Hey team, Vikram here leaving a quick voice memo after a 45-minute escalation call with our logistics partner BlueDart.
We had 14 delayed shipments this week causing customer chargebacks and 1-star reviews.
Effective immediately, I've decided to update our customer refund policy: any delayed order past 5 days gets an instant 100% full refund plus a ₹500 credit voucher, no questions asked.
I considered just offering a 20% discount coupon, but that won't restore trust with high-value customers. We also rejected switching couriers immediately because onboarding a replacement takes 3 weeks mid-quarter.
Sneha, you take ownership of configuring this auto-refund rule in Zendesk by tomorrow. Budget allowance for goodwill credits is ₹50,000 for this month. Let's move fast on this.`,

    conflict_office: `[18/11/26, 3:30 PM] Rohit Verma: Team, effective January 1st, we need to mandate 3 days in-office attendance for all engineers. In-person collaboration is needed.
[18/11/26, 3:32 PM] Neha Tandon: Wait Rohit, didn't we decide on a 100% permanent Remote-First policy back in September and downsize our Bangalore office?
[18/11/26, 3:35 PM] Rohit Verma: Team productivity is dropping without face-to-face meetings. Let's make office attendance mandatory.
[18/11/26, 3:38 PM] Vikram Malhotra: This conflicts with our existing company policy DEC-2026-003. We need to evaluate before proceeding.`,

    conflict_stripe: `[19/11/26, 11:00 AM] Kunal Shah: We should switch to Stripe exclusively for all payments in India and internationally. Having two payment gateways (Razorpay + Stripe) is confusing accounting.
[19/11/26, 11:04 AM] Ananya Sen: But Kunal, Razorpay has 94% success on Indian UPI, and Stripe failed 20% of Indian cards previously.
[19/11/26, 11:06 AM] Kunal Shah: Stripe just launched new UPI APIs. Let's standardize on Stripe for all Indian and global billing by next week.`,

    conflict_discount: `[15/11/26, 2:15 PM] Sameer (Sales): Hey team, BigTech Corp wants a 25% discount to close the deal before Friday. Deal value is ₹18 Lakhs.
[15/11/26, 2:18 PM] Rohan Kapoor: Remember our sales policy DEC-2026-004 caps all discounts at 15%. Anything above 15% requires written CEO sign-off.
[15/11/26, 2:20 PM] Sameer (Sales): CEO is on a flight to London. Can we just approve the 25% discount now so we don't lose the deal?`
};

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    setupKeyboardShortcuts();
});

function initApp() {
    lucide.createIcons();
    fetchDashboardStats();
    fetchDecisions();
    fetchTasks();
}

function setupKeyboardShortcuts() {
    window.addEventListener('keydown', (e) => {
        if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
            e.preventDefault();
            const searchInput = document.getElementById('global-search-input');
            if (searchInput) searchInput.focus();
        }
        if (e.key === 'Escape') {
            closeAllModals();
        }
    });

    const globalSearch = document.getElementById('global-search-input');
    if (globalSearch) {
        globalSearch.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            if (currentTab !== 'vault') {
                switchTab('vault');
            }
            const vaultSearch = document.getElementById('vault-search-input');
            if (vaultSearch) vaultSearch.value = query;
            debounceFetchDecisions();
        });
    }
}

// -------------------------------------------------------------
// Tab Switching
// -------------------------------------------------------------
function switchTab(tabName) {
    currentTab = tabName;
    const views = ['dashboard', 'vault', 'import-chat', 'conflicts', 'tasks', 'outcomes', 'ask-memory'];
    views.forEach(v => {
        const el = document.getElementById(`view-${v}`);
        if (el) el.classList.add('hidden');
        const btn = document.getElementById(`tab-btn-${v === 'import-chat' ? 'import' : v}`);
        if (btn) {
            btn.className = "tab-button flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all text-slate-400 hover:text-slate-200 hover:bg-slate-800/60";
        }
    });

    const activeView = document.getElementById(`view-${tabName}`);
    if (activeView) activeView.classList.remove('hidden');

    const activeBtn = document.getElementById(`tab-btn-${tabName === 'import-chat' ? 'import' : tabName}`);
    if (activeBtn) {
        activeBtn.className = "tab-button flex items-center gap-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all text-brand-400 bg-brand-500/10 border border-brand-500/20";
    }

    if (tabName === 'dashboard') fetchDashboardStats();
    if (tabName === 'vault') fetchDecisions();
    if (tabName === 'tasks') fetchTasks();
    if (tabName === 'conflicts') renderConflictsView();
    if (tabName === 'outcomes') renderOutcomesView();

    lucide.createIcons();
}

// -------------------------------------------------------------
// Dashboard & Analytics
// -------------------------------------------------------------
async function fetchDashboardStats() {
    try {
        const res = await fetch('/api/dashboard/stats');
        const data = await res.json();
        cachedStats = data;

        // Update Stats Counters
        document.getElementById('stat-total-decisions').textContent = data.total_decisions;
        document.getElementById('stat-active-decisions').textContent = data.active_decisions;
        document.getElementById('stat-success-rate').textContent = `${data.success_rate_percent}%`;
        document.getElementById('stat-pending-tasks').textContent = data.pending_tasks;
        document.getElementById('stat-overdue-tasks').textContent = `${data.overdue_tasks} overdue`;
        document.getElementById('stat-conflicts').textContent = data.unresolved_conflicts;
        document.getElementById('stat-pending-outcomes').textContent = data.pending_outcomes;

        // Nav Badges
        document.getElementById('badge-total-decisions').textContent = data.total_decisions;
        document.getElementById('badge-active-conflicts').textContent = data.unresolved_conflicts;
        document.getElementById('badge-pending-tasks').textContent = data.pending_tasks;
        document.getElementById('badge-pending-outcomes').textContent = data.pending_outcomes;

        // Render Charts
        renderCharts(data);

        // Render Recent Activity Feed
        renderRecentActivity(data.recent_activity || []);

        // Render Spotlight Decisions
        renderDashboardSpotlight();
    } catch (err) {
        console.error("Failed to load dashboard stats:", err);
    }
}

function renderCharts(data) {
    // 1. Department Chart
    const deptCtx = document.getElementById('chart-departments');
    if (deptCtx) {
        if (deptChartInstance) deptChartInstance.destroy();
        const depts = Object.keys(data.decisions_by_dept || {});
        const counts = Object.values(data.decisions_by_dept || {});
        deptChartInstance = new Chart(deptCtx, {
            type: 'doughnut',
            data: {
                labels: depts.length ? depts : ['No Data'],
                datasets: [{
                    data: counts.length ? counts : [1],
                    backgroundColor: ['#6366f1', '#10b981', '#f59e0b', '#3b82f6', '#ec4899', '#8b5cf6'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#94a3b8', font: { size: 11 }, boxWidth: 12 }
                    }
                },
                cutout: '68%'
            }
        });
    }

    // 2. Status Chart
    const statusCtx = document.getElementById('chart-statuses');
    if (statusCtx) {
        if (statusChartInstance) statusChartInstance.destroy();
        const statuses = Object.keys(data.decisions_by_status || {});
        const sCounts = Object.values(data.decisions_by_status || {});
        statusChartInstance = new Chart(statusCtx, {
            type: 'bar',
            data: {
                labels: statuses.length ? statuses : ['No Data'],
                datasets: [{
                    label: 'Decisions',
                    data: sCounts.length ? sCounts : [0],
                    backgroundColor: '#10b981',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { display: false } },
                    y: { ticks: { color: '#94a3b8', font: { size: 10 }, stepSize: 1 }, grid: { color: '#1e293b' } }
                }
            }
        });
    }
}

function renderRecentActivity(activities) {
    const feed = document.getElementById('recent-activity-feed');
    if (!feed) return;
    if (!activities.length) {
        feed.innerHTML = `<p class="text-slate-500 py-4 text-center">No recent activity recorded.</p>`;
        return;
    }

    feed.innerHTML = activities.slice(0, 6).map(act => {
        const timeStr = act.timestamp ? act.timestamp.split('T')[0] : 'Today';
        return `
            <div class="flex items-start gap-2.5 pb-2 border-b border-slate-800/80 last:border-0">
                <span class="w-1.5 h-1.5 rounded-full bg-brand-400 mt-1.5 shrink-0"></span>
                <div class="flex-1 min-w-0">
                    <div class="flex items-center justify-between gap-1">
                        <span class="font-semibold text-slate-200 truncate">${act.decision_code || 'DEC'}</span>
                        <span class="text-[10px] text-slate-500 font-mono">${timeStr}</span>
                    </div>
                    <p class="text-slate-400 truncate text-[11px]">${act.details}</p>
                </div>
            </div>
        `;
    }).join('');
}

async function renderDashboardSpotlight() {
    const container = document.getElementById('dashboard-recent-cards');
    if (!container) return;
    if (!cachedDecisions.length) {
        await fetchDecisions();
    }
    const spotlight = cachedDecisions.slice(0, 3);
    container.innerHTML = spotlight.map(renderDecisionCardHtml).join('');
    lucide.createIcons();
}

// -------------------------------------------------------------
// Decision Vault & Listing
// -------------------------------------------------------------
function debounceFetchDecisions() {
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(() => {
        fetchDecisions();
    }, 250);
}

async function fetchDecisions() {
    const dept = document.getElementById('filter-department')?.value || 'all';
    const status = document.getElementById('filter-status')?.value || 'all';
    const outcome = document.getElementById('filter-outcome')?.value || 'all';
    const search = document.getElementById('vault-search-input')?.value || '';

    const params = new URLSearchParams();
    if (dept !== 'all') params.append('department', dept);
    if (status !== 'all') params.append('status', status);
    if (outcome !== 'all') params.append('outcome_status', outcome);
    if (search.trim()) params.append('search', search.trim());

    try {
        const res = await fetch(`/api/decisions?${params.toString()}`);
        const data = await res.json();
        cachedDecisions = data.items || [];

        const countInd = document.getElementById('vault-count-indicator');
        if (countInd) countInd.textContent = `Showing ${cachedDecisions.length} decisions`;

        const container = document.getElementById('vault-cards-container');
        if (container) {
            if (!cachedDecisions.length) {
                container.innerHTML = `
                    <div class="col-span-full py-16 text-center space-y-3">
                        <i data-lucide="search-x" class="w-10 h-10 text-slate-600 mx-auto"></i>
                        <h4 class="text-sm font-semibold text-slate-300">No decisions match your filter criteria</h4>
                        <p class="text-xs text-slate-500">Try adjusting the department, status, or search terms.</p>
                    </div>
                `;
            } else {
                container.innerHTML = cachedDecisions.map(renderDecisionCardHtml).join('');
            }
        }
        lucide.createIcons();
    } catch (err) {
        console.error("Failed to fetch decisions:", err);
    }
}

function renderDecisionCardHtml(d) {
    const statusBadgeClass = {
        'ACTIVE': 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
        'IMPLEMENTED': 'bg-blue-500/10 text-blue-400 border border-blue-500/20',
        'SUPERSEDED': 'bg-slate-700/50 text-slate-400 border border-slate-600/50',
        'DRAFT': 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
    }[d.status] || 'bg-slate-800 text-slate-400';

    const outcomeBadge = {
        'SUCCESS': '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✓ SUCCESS</span>',
        'PARTIAL_SUCCESS': '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">~ PARTIAL</span>',
        'FAILED': '<span class="text-[10px] font-bold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">✕ FAILED</span>',
        'PENDING_EVALUATION': '<span class="text-[10px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">⏳ Pending Eval</span>'
    }[d.outcome_status] || '';

    const altsCount = (d.rejected_alternatives || []).length;
    const taskCount = d.task_count || 0;
    const completedTasks = d.completed_task_count || 0;
    const healthPercent = d.health_score || 0;

    return `
        <div class="decision-card bg-slate-800/50 border border-slate-700/60 hover:border-brand-500/40 rounded-2xl p-5 flex flex-col justify-between space-y-4 shadow-sm">
            <!-- Header Badges -->
            <div class="space-y-2">
                <div class="flex items-center justify-between gap-2">
                    <span class="text-xs font-mono font-bold px-2.5 py-0.5 rounded bg-brand-500/15 text-brand-300 border border-brand-500/30">${d.decision_code}</span>
                    <div class="flex items-center gap-1.5">
                        <span class="text-[11px] font-medium px-2 py-0.5 rounded ${statusBadgeClass}">${d.status}</span>
                        ${outcomeBadge}
                    </div>
                </div>

                <!-- Title -->
                <h3 class="text-sm font-bold text-white hover:text-brand-300 cursor-pointer transition-colors leading-snug" onclick="openDecisionDetail(${d.id})">
                    ${d.title}
                </h3>
            </div>

            <!-- Context & Why Snippet -->
            <div class="space-y-2 text-xs">
                <p class="text-slate-300 line-clamp-2 leading-relaxed">
                    <span class="text-slate-500 font-semibold">Why: </span>${d.reasoning || d.problem_context}
                </p>

                <!-- Rejected Alternatives Chip -->
                ${altsCount > 0 ? `
                    <div class="flex items-center gap-1.5 text-[11px] text-slate-400 bg-slate-900/60 px-2.5 py-1 rounded-lg border border-slate-800">
                        <i data-lucide="x-circle" class="w-3.5 h-3.5 text-rose-400"></i>
                        <span>${altsCount} rejected alternative${altsCount > 1 ? 's' : ''} evaluated</span>
                    </div>
                ` : ''}
            </div>

            <!-- Execution Progress & Meta -->
            <div class="pt-3 border-t border-slate-700/60 space-y-3 text-xs">
                <!-- Task Progress Bar -->
                <div>
                    <div class="flex items-center justify-between text-[11px] text-slate-400 mb-1">
                        <span>Tasks Executed</span>
                        <span class="font-mono text-slate-300">${completedTasks}/${taskCount} (${healthPercent}%)</span>
                    </div>
                    <div class="w-full h-1.5 rounded-full bg-slate-700 overflow-hidden">
                        <div class="h-full bg-brand-500 rounded-full transition-all duration-500" style="width: ${healthPercent}%"></div>
                    </div>
                </div>

                <!-- Owner & Actions Footer -->
                <div class="flex items-center justify-between pt-1">
                    <div class="flex items-center gap-2 text-slate-300 text-[11px]">
                        <div class="w-6 h-6 rounded-full bg-brand-700 flex items-center justify-center text-[10px] font-bold text-white uppercase">
                            ${d.owner_name.charAt(0)}
                        </div>
                        <span class="truncate max-w-[110px] font-medium">${d.owner_name}</span>
                    </div>

                    <div class="flex items-center gap-1">
                        <button onclick="exportWhatsApp(${d.id})" title="Export WhatsApp Broadcast" class="p-1.5 text-emerald-400 hover:bg-emerald-500/10 rounded-lg transition-all">
                            <i data-lucide="share-2" class="w-3.5 h-3.5"></i>
                        </button>
                        <button onclick="openOutcomeModal(${d.id})" title="Record Retrospective" class="p-1.5 text-amber-400 hover:bg-amber-500/10 rounded-lg transition-all">
                            <i data-lucide="target" class="w-3.5 h-3.5"></i>
                        </button>
                        <button onclick="openDecisionDetail(${d.id})" class="px-2.5 py-1 text-xs font-semibold bg-slate-700/80 hover:bg-slate-700 text-slate-200 rounded-lg transition-all">
                            View
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;
}

// -------------------------------------------------------------
// Decision Detail Modal
// -------------------------------------------------------------
async function openDecisionDetail(id) {
    try {
        const res = await fetch(`/api/decisions/${id}`);
        const d = await res.json();

        document.getElementById('modal-detail-code').textContent = d.decision_code;
        document.getElementById('modal-detail-dept').textContent = d.department;
        document.getElementById('modal-detail-status').textContent = d.status;
        document.getElementById('modal-detail-title').textContent = d.title;
        document.getElementById('modal-detail-problem').textContent = `Problem Context: "${d.problem_context}"`;
        document.getElementById('modal-detail-decision').textContent = d.decision_text;
        document.getElementById('modal-detail-reasoning').textContent = d.reasoning;
        document.getElementById('modal-detail-owner').textContent = `${d.owner_name} (${d.owner_role || 'Lead'})`;
        document.getElementById('modal-detail-deadline').textContent = d.deadline_date || 'None set';
        document.getElementById('modal-detail-budget').textContent = d.budget_or_cost || 'N/A';
        document.getElementById('modal-detail-source').textContent = d.source_type || 'direct';

        // Rejected Alternatives
        const altsContainer = document.getElementById('modal-detail-alts');
        if (d.rejected_alternatives && d.rejected_alternatives.length) {
            altsContainer.innerHTML = d.rejected_alternatives.map(a => `
                <div class="bg-slate-800/60 border border-slate-700/60 p-2.5 rounded-xl flex items-start gap-2">
                    <i data-lucide="x" class="w-4 h-4 text-rose-400 mt-0.5 shrink-0"></i>
                    <div>
                        <span class="font-bold text-slate-200">${a.alternative}</span>
                        <p class="text-slate-400 text-[11px] mt-0.5">${a.reason_rejected}</p>
                    </div>
                </div>
            `).join('');
        } else {
            altsContainer.innerHTML = `<p class="text-slate-500 italic">No alternative options recorded as rejected for this decision.</p>`;
        }

        // Outcome Retrospective Block
        const outcomeBadge = document.getElementById('modal-detail-outcome-badge');
        outcomeBadge.textContent = d.outcome_status;
        outcomeBadge.className = `px-2 py-0.5 rounded text-[11px] font-semibold ${
            d.outcome_status === 'SUCCESS' ? 'bg-emerald-500/20 text-emerald-300' :
            d.outcome_status === 'PARTIAL_SUCCESS' ? 'bg-amber-500/20 text-amber-300' :
            d.outcome_status === 'FAILED' ? 'bg-rose-500/20 text-rose-300' : 'bg-slate-800 text-slate-400'
        }`;
        document.getElementById('modal-detail-expected').textContent = `Target Expected KPI: ${d.expected_outcome || 'N/A'}`;
        document.getElementById('modal-detail-outcome-notes').textContent = d.outcome_notes ? `Retrospective Result: ${d.outcome_notes}` : 'Retrospective pending evaluation.';

        const lessonsBox = document.getElementById('modal-detail-lessons-box');
        if (d.lessons_learned) {
            lessonsBox.classList.remove('hidden');
            document.getElementById('modal-detail-lessons').textContent = d.lessons_learned;
        } else {
            lessonsBox.classList.add('hidden');
        }

        // Tasks
        const tasksContainer = document.getElementById('modal-detail-tasks');
        if (d.tasks && d.tasks.length) {
            tasksContainer.innerHTML = d.tasks.map(t => `
                <div class="bg-slate-800/40 border border-slate-700/60 p-2.5 rounded-xl flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2">
                        <button onclick="toggleTaskStatus(${t.id}, '${t.status === 'COMPLETED' ? 'PENDING' : 'COMPLETED'}')" class="p-1 rounded text-slate-400 hover:text-emerald-400">
                            <i data-lucide="${t.status === 'COMPLETED' ? 'check-circle-2' : 'circle'}" class="w-4 h-4 ${t.status === 'COMPLETED' ? 'text-emerald-400' : ''}"></i>
                        </button>
                        <span class="${t.status === 'COMPLETED' ? 'line-through text-slate-500' : 'text-slate-200'} font-medium">${t.title}</span>
                    </div>
                    <div class="flex items-center gap-2 text-[11px] text-slate-400 font-mono">
                        <span>@${t.assignee}</span>
                        <span>Due: ${t.due_date || 'N/A'}</span>
                    </div>
                </div>
            `).join('');
        } else {
            tasksContainer.innerHTML = `<p class="text-slate-500 italic">No execution tasks currently attached to this decision.</p>`;
        }

        // Raw Source Transcript
        document.getElementById('modal-detail-raw').textContent = d.raw_source_text || 'No raw transcript recorded (Logged directly via form).';

        // Action Buttons Wiring
        document.getElementById('modal-btn-export-wa').onclick = () => exportWhatsApp(d.id);
        document.getElementById('modal-btn-eval-outcome').onclick = () => {
            closeModal('modal-decision-detail');
            openOutcomeModal(d.id);
        };
        document.getElementById('modal-btn-add-task').onclick = () => {
            const taskTitle = prompt(`Add a new task for ${d.decision_code}:`);
            if (taskTitle) {
                quickAddTask(d.id, taskTitle, d.owner_name);
            }
        };

        openModal('modal-decision-detail');
        lucide.createIcons();
    } catch (err) {
        console.error("Failed to load decision detail:", err);
    }
}

// -------------------------------------------------------------
// Omnichannel Importer: Chat • Meetings • Voice Recording
// -------------------------------------------------------------
let currentImportMode = 'text';
let uploadedFileObject = null;
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];
let speechRecognizer = null;
let recordTimerInterval = null;
let recordSeconds = 0;

function switchImportMode(mode) {
    currentImportMode = mode;
    ['text', 'file', 'voice'].forEach(m => {
        const pane = document.getElementById(`import-pane-${m}`);
        const btn = document.getElementById(`import-mode-btn-${m}`);
        if (pane) pane.classList.add('hidden');
        if (btn) {
            btn.className = "px-3.5 py-1.5 rounded-xl text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 flex items-center gap-1.5 transition-all";
        }
    });

    const activePane = document.getElementById(`import-pane-${mode}`);
    const activeBtn = document.getElementById(`import-mode-btn-${mode}`);
    if (activePane) activePane.classList.remove('hidden');
    if (activeBtn) {
        activeBtn.className = "px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5 transition-all";
    }
    lucide.createIcons();
}

function handleFileSelected(event) {
    const file = event.target.files[0];
    if (!file) return;
    uploadedFileObject = file;

    const preview = document.getElementById('uploaded-file-preview');
    document.getElementById('uploaded-filename').textContent = file.name;
    document.getElementById('uploaded-filesize').textContent = `${(file.size / 1024).toFixed(1)} KB • ${file.type || 'Document'}`;
    if (preview) preview.classList.remove('hidden');
    lucide.createIcons();
}

async function processUploadedFile() {
    if (!uploadedFileObject) {
        alert("Please select a file to process!");
        return;
    }

    const btn = document.getElementById('btn-process-file');
    btn.disabled = true;
    btn.innerHTML = `<i data-lucide="loader-2" class="w-3.5 h-3.5 animate-spin"></i><span>Processing File...</span>`;
    lucide.createIcons();

    const formData = new FormData();
    formData.append('file', uploadedFileObject);
    formData.append('source_type', 'meeting');

    try {
        const res = await fetch('/api/decisions/upload-file', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            const ext = data.extracted;
            extractedDecisionCache = ext;
            extractedDecisionCache.raw_source_text = data.raw_text;
            extractedDecisionCache.source_type = data.source_type;

            // Also copy to raw text area in case user toggles to text
            const rawArea = document.getElementById('raw-chat-input');
            if (rawArea) rawArea.value = data.raw_text;

            // Populate extracted fields
            document.getElementById('extract-title').value = ext.title;
            document.getElementById('extract-department').value = ext.department;
            document.getElementById('extract-owner').value = ext.owner_name;
            document.getElementById('extract-decision').value = ext.decision_text;
            document.getElementById('extract-reasoning').value = ext.reasoning;

            // Rejected Alternatives
            const altsList = document.getElementById('extract-rejected-list');
            if (ext.rejected_alternatives && ext.rejected_alternatives.length) {
                altsList.innerHTML = ext.rejected_alternatives.map(a => `
                    <div class="bg-slate-800 p-2 rounded-lg border border-slate-700/80 flex items-start gap-2">
                        <i data-lucide="x" class="w-3.5 h-3.5 text-rose-400 mt-0.5"></i>
                        <div>
                            <span class="font-bold text-slate-200">${a.alternative}</span>
                            <p class="text-slate-400 text-[11px]">${a.reason_rejected}</p>
                        </div>
                    </div>
                `).join('');
            } else {
                altsList.innerHTML = `<span class="text-slate-500 italic">None detected automatically.</span>`;
            }

            // Tasks
            const tasksList = document.getElementById('extract-tasks-list');
            if (ext.tasks && ext.tasks.length) {
                tasksList.innerHTML = ext.tasks.map(t => `
                    <div class="bg-slate-800 p-1.5 rounded-lg flex items-center justify-between gap-2 text-[11px]">
                        <span class="text-slate-200 truncate">• ${t.title}</span>
                        <span class="text-emerald-400 font-mono">@${t.assignee}</span>
                    </div>
                `).join('');
            } else {
                tasksList.innerHTML = `<span class="text-slate-500 italic">No specific tasks extracted.</span>`;
            }

            // Conflict Banner
            const conflictBanner = document.getElementById('extraction-conflict-banner');
            if (data.conflict_count > 0) {
                conflictBanner.classList.remove('hidden');
                const c = data.conflicts[0];
                document.getElementById('extraction-conflict-text').innerHTML = `
                    <strong>${c.conflict_type} [${c.severity}]:</strong> ${c.explanation}<br>
                    <em class="text-slate-300 mt-1 block">💡 Suggested Action: ${c.suggested_action}</em>
                `;
            } else {
                conflictBanner.classList.add('hidden');
            }

            // Show Results
            document.getElementById('extraction-empty-state').classList.add('hidden');
            document.getElementById('extraction-results').classList.remove('hidden');
        } else {
            alert("File processing failed.");
        }
    } catch (err) {
        console.error("File upload error:", err);
        alert("Upload error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i data-lucide="sparkles" class="w-3.5 h-3.5"></i><span>Process File</span>`;
        lucide.createIcons();
    }
}

// -------------------------------------------------------------
// Live Voice Memo Recording (Web Speech API + MediaRecorder)
// -------------------------------------------------------------
async function toggleVoiceRecording() {
    if (isRecording) {
        stopVoiceRecording();
    } else {
        startVoiceRecording();
    }
}

async function startVoiceRecording() {
    isRecording = true;
    recordSeconds = 0;
    audioChunks = [];

    // UI Updates
    document.getElementById('mic-status-indicator').className = "w-16 h-16 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center mx-auto ring-4 ring-rose-500/30 animate-pulse";
    document.getElementById('mic-heading').textContent = "Listening & Transcribing Voice Memo...";
    document.getElementById('mic-subheading').textContent = "Speak clearly into your microphone. Say what was decided, why, and who owns what.";
    document.getElementById('btn-start-record').className = "px-5 py-2.5 rounded-xl bg-slate-700 hover:bg-slate-600 text-white text-xs font-bold flex items-center gap-2 shadow-lg transition-all";
    document.getElementById('btn-record-label').textContent = "Stop Recording";
    document.getElementById('voice-timer-display').classList.remove('hidden');

    recordTimerInterval = setInterval(() => {
        recordSeconds++;
        const mins = String(Math.floor(recordSeconds / 60)).padStart(2, '0');
        const secs = String(recordSeconds % 60).padStart(2, '0');
        document.getElementById('voice-timer-text').textContent = `${mins}:${secs}`;
    }, 1000);

    const livePreview = document.getElementById('live-speech-preview');
    livePreview.textContent = "";

    // 1. Web Speech API (Client-side real-time streaming speech-to-text)
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        speechRecognizer = new SpeechRecognition();
        speechRecognizer.continuous = true;
        speechRecognizer.interimResults = true;
        speechRecognizer.lang = 'en-US';

        speechRecognizer.onresult = (event) => {
            let transcript = '';
            for (let i = 0; i < event.results.length; i++) {
                transcript += event.results[i][0].transcript + ' ';
            }
            livePreview.textContent = transcript.trim();
        };

        speechRecognizer.onerror = (e) => {
            console.warn("Speech recognition notice:", e.error);
        };

        try {
            speechRecognizer.start();
        } catch (e) {
            console.warn("Could not start speech recognition:", e);
        }
    } else {
        livePreview.textContent = "(Live browser speech-to-text not supported in this browser. Recording audio for processing...)";
    }

    // 2. MediaRecorder (Audio capture for playback)
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = (e) => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };
        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            const audioUrl = URL.createObjectURL(audioBlob);
            const player = document.getElementById('audio-playback');
            if (player) {
                player.src = audioUrl;
                document.getElementById('audio-playback-container').classList.remove('hidden');
            }
        };
        mediaRecorder.start();
    } catch (err) {
        console.warn("Microphone access unavailable or denied:", err);
    }
}

function stopVoiceRecording() {
    isRecording = false;
    clearInterval(recordTimerInterval);

    // Stop MediaRecorder
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }

    // Stop SpeechRecognizer
    if (speechRecognizer) {
        try { speechRecognizer.stop(); } catch(e){}
    }

    // UI Reset
    document.getElementById('mic-status-indicator').className = "w-16 h-16 rounded-full bg-slate-800 text-slate-400 flex items-center justify-center mx-auto transition-all";
    document.getElementById('mic-heading').textContent = "Voice Memo Recorded";
    document.getElementById('mic-subheading').textContent = "Voice note transcribed! Analyzing decision details now...";
    document.getElementById('btn-start-record').className = "px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg shadow-rose-600/30 transition-all";
    document.getElementById('btn-record-label').textContent = "Record Another Note";

    // Grab transcribed text
    const liveText = document.getElementById('live-speech-preview').textContent.trim();
    if (liveText && !liveText.startsWith('(')) {
        document.getElementById('raw-chat-input').value = liveText;
        document.getElementById('char-count').textContent = `${liveText.length} characters`;
        // Trigger extraction automatically!
        analyzeChatTranscript();
    } else {
        // If user didn't speak or mic had no input, offer sample voice memo
        const sampleVoice = SAMPLE_CHATS['voice_refund'];
        document.getElementById('live-speech-preview').textContent = sampleVoice;
        document.getElementById('raw-chat-input').value = sampleVoice;
        document.getElementById('char-count').textContent = `${sampleVoice.length} characters`;
        analyzeChatTranscript();
    }
    lucide.createIcons();
}

function loadSampleScenario() {
    const val = document.getElementById('sample-scenario-select').value;
    if (val && SAMPLE_CHATS[val]) {
        // Auto-switch mode based on scenario type
        if (val.startsWith('meeting_')) {
            switchImportMode('file');
            document.getElementById('uploaded-filename').textContent = "strategy_sync_exec.vtt";
            document.getElementById('uploaded-filesize').textContent = "2.4 KB • WebVTT Meeting Subtitle";
            document.getElementById('uploaded-file-preview').classList.remove('hidden');
        } else if (val.startsWith('voice_')) {
            switchImportMode('voice');
            document.getElementById('live-speech-preview').textContent = SAMPLE_CHATS[val];
            document.getElementById('mic-heading').textContent = "Sample Voice Memo Loaded";
            document.getElementById('mic-subheading').textContent = "45-second audio memo transcribed from WhatsApp voice note.";
        } else {
            switchImportMode('text');
        }

        document.getElementById('raw-chat-input').value = SAMPLE_CHATS[val];
        document.getElementById('char-count').textContent = `${SAMPLE_CHATS[val].length} characters`;
        analyzeChatTranscript();
    }
}

function clearChatInput() {
    document.getElementById('raw-chat-input').value = '';
    document.getElementById('char-count').textContent = '0 characters';
    document.getElementById('extraction-results').classList.add('hidden');
    document.getElementById('extraction-empty-state').classList.remove('hidden');
}

async function analyzeChatTranscript() {
    const rawText = document.getElementById('raw-chat-input').value.trim();
    if (!rawText) {
        alert("Please paste chat text or select a sample scenario first!");
        return;
    }

    const parseBtn = document.getElementById('btn-parse-chat');
    parseBtn.disabled = true;
    parseBtn.innerHTML = `<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i><span>Analyzing Discussion...</span>`;
    lucide.createIcons();

    try {
        // 1. Call Chat Parser API
        const res = await fetch('/api/decisions/parse-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ chat_text: rawText })
        });
        const data = await res.json();
        const ext = data.extracted;
        extractedDecisionCache = ext;
        extractedDecisionCache.raw_source_text = rawText;

        // Populate fields
        document.getElementById('extract-title').value = ext.title;
        document.getElementById('extract-department').value = ext.department;
        document.getElementById('extract-owner').value = ext.owner_name;
        document.getElementById('extract-decision').value = ext.decision_text;
        document.getElementById('extract-reasoning').value = ext.reasoning;

        // Rejected Alternatives list
        const altsList = document.getElementById('extract-rejected-list');
        if (ext.rejected_alternatives && ext.rejected_alternatives.length) {
            altsList.innerHTML = ext.rejected_alternatives.map(a => `
                <div class="bg-slate-800 p-2 rounded-lg border border-slate-700/80 flex items-start gap-2">
                    <i data-lucide="x" class="w-3.5 h-3.5 text-rose-400 mt-0.5"></i>
                    <div>
                        <span class="font-bold text-slate-200">${a.alternative}</span>
                        <p class="text-slate-400 text-[11px]">${a.reason_rejected}</p>
                    </div>
                </div>
            `).join('');
        } else {
            altsList.innerHTML = `<span class="text-slate-500 italic">None detected automatically.</span>`;
        }

        // Tasks list
        const tasksList = document.getElementById('extract-tasks-list');
        if (ext.tasks && ext.tasks.length) {
            tasksList.innerHTML = ext.tasks.map(t => `
                <div class="bg-slate-800 p-1.5 rounded-lg flex items-center justify-between gap-2 text-[11px]">
                    <span class="text-slate-200 truncate">• ${t.title}</span>
                    <span class="text-emerald-400 font-mono">@${t.assignee}</span>
                </div>
            `).join('');
        } else {
            tasksList.innerHTML = `<span class="text-slate-500 italic">No specific tasks extracted.</span>`;
        }

        // 2. Check for AI Conflict Radar in real-time
        const conflictRes = await fetch('/api/decisions/check-conflicts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: ext.title,
                decision_text: ext.decision_text,
                department: ext.department,
                category: ext.category
            })
        });
        const conflictData = await conflictRes.json();

        const conflictBanner = document.getElementById('extraction-conflict-banner');
        if (conflictData.has_conflicts) {
            conflictBanner.classList.remove('hidden');
            const c = conflictData.conflicts[0];
            document.getElementById('extraction-conflict-text').innerHTML = `
                <strong>${c.conflict_type} [${c.severity}]:</strong> ${c.explanation}<br>
                <em class="text-slate-300 mt-1 block">💡 Suggested Action: ${c.suggested_action}</em>
            `;
        } else {
            conflictBanner.classList.add('hidden');
        }

        // Show results box
        document.getElementById('extraction-empty-state').classList.add('hidden');
        document.getElementById('extraction-results').classList.remove('hidden');
        lucide.createIcons();
    } catch (err) {
        console.error("Chat parsing failed:", err);
        alert("Chat parsing error: " + err.message);
    } finally {
        parseBtn.disabled = false;
        parseBtn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4"></i><span>Extract Decision & Check Conflicts</span>`;
        lucide.createIcons();
    }
}

async function saveExtractedDecision() {
    if (!extractedDecisionCache) return;

    // Read any edits the user made
    const payload = {
        title: document.getElementById('extract-title').value,
        department: document.getElementById('extract-department').value,
        category: extractedDecisionCache.category || 'Operations',
        problem_context: extractedDecisionCache.problem_context,
        decision_text: document.getElementById('extract-decision').value,
        reasoning: document.getElementById('extract-reasoning').value,
        rejected_alternatives: extractedDecisionCache.rejected_alternatives || [],
        owner_name: document.getElementById('extract-owner').value,
        owner_role: "Lead",
        participants: extractedDecisionCache.participants || [],
        source_type: "whatsapp",
        raw_source_text: extractedDecisionCache.raw_source_text,
        deadline_date: extractedDecisionCache.deadline_date,
        budget_or_cost: extractedDecisionCache.budget_or_cost || '',
        status: "ACTIVE",
        expected_outcome: extractedDecisionCache.expected_outcome || '',
        outcome_status: "PENDING_EVALUATION",
        tags: extractedDecisionCache.tags || [],
        tasks: extractedDecisionCache.tasks || []
    };

    try {
        const res = await fetch('/api/decisions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (result.success) {
            alert(`✅ Decision successfully logged into Decision Memory as ${result.decision.decision_code}!`);
            clearChatInput();
            switchTab('vault');
            fetchDashboardStats();
        }
    } catch (err) {
        console.error("Failed to save decision:", err);
        alert("Failed to save decision: " + err.message);
    }
}

// -------------------------------------------------------------
// AI Conflict Radar View & Demo
// -------------------------------------------------------------
async function renderConflictsView() {
    const container = document.getElementById('conflicts-container');
    if (!container) return;

    try {
        // Query conflicts from database or live test conflicts across active decisions
        const res = await fetch('/api/decisions?status=ACTIVE');
        const data = await res.json();
        const activeDecs = data.items || [];

        // Check conflicts among active decisions
        const detectedConflicts = [];
        for (let i = 0; i < activeDecs.length; i++) {
            const dec = activeDecs[i];
            const checkRes = await fetch('/api/decisions/check-conflicts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: dec.title,
                    decision_text: dec.decision_text,
                    department: dec.department,
                    category: dec.category,
                    current_id: dec.id
                })
            });
            const cData = await checkRes.json();
            if (cData.has_conflicts) {
                cData.conflicts.forEach(c => {
                    if (!detectedConflicts.some(existing => 
                        (existing.id_a === dec.id && existing.id_b === c.conflicting_decision_id) ||
                        (existing.id_b === dec.id && existing.id_a === c.conflicting_decision_id)
                    )) {
                        detectedConflicts.push({
                            id_a: dec.id,
                            code_a: dec.decision_code,
                            title_a: dec.title,
                            owner_a: dec.owner_name,
                            id_b: c.conflicting_decision_id,
                            code_b: c.conflicting_decision_code,
                            title_b: c.conflicting_title,
                            type: c.conflict_type,
                            severity: c.severity,
                            explanation: c.explanation,
                            action: c.suggested_action
                        });
                    }
                });
            }
        }

        if (!detectedConflicts.length) {
            container.innerHTML = `
                <div class="bg-slate-900/60 border border-slate-800 rounded-2xl p-10 text-center space-y-3">
                    <div class="w-12 h-12 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto text-emerald-400">
                        <i data-lucide="shield-check" class="w-6 h-6"></i>
                    </div>
                    <h3 class="text-sm font-bold text-white">No Active Policy Conflicts in Vault</h3>
                    <p class="text-xs text-slate-400 max-w-sm mx-auto">
                        All currently active decisions align consistently with historical company memory.
                    </p>
                    <button onclick="testConflictDemo()" class="mt-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs text-amber-300 font-semibold border border-amber-500/30">
                        ⚡ Simulate a Conflict Scenario
                    </button>
                </div>
            `;
        } else {
            container.innerHTML = detectedConflicts.map(c => `
                <div class="bg-slate-900 border border-rose-500/40 rounded-2xl p-5 space-y-4 shadow-lg">
                    <div class="flex items-center justify-between">
                        <div class="flex items-center gap-2">
                            <span class="text-xs font-bold px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-400 border border-rose-500/30">
                                ⚠️ ${c.type} [${c.severity}]
                            </span>
                        </div>
                        <span class="text-xs text-slate-400 font-mono">Collision between ${c.code_a} & ${c.code_b}</span>
                    </div>

                    <!-- Comparison Grid -->
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                        <div class="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700 space-y-1">
                            <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">${c.code_a} (Owner: ${c.owner_a})</span>
                            <p class="font-semibold text-slate-100">${c.title_a}</p>
                        </div>
                        <div class="bg-slate-800/60 p-3.5 rounded-xl border border-slate-700 space-y-1">
                            <span class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">${c.code_b}</span>
                            <p class="font-semibold text-slate-100">${c.title_b}</p>
                        </div>
                    </div>

                    <!-- Explanation -->
                    <div class="bg-rose-950/30 border border-rose-500/30 p-3 rounded-xl text-xs text-rose-200 leading-relaxed">
                        <strong>AI Diagnosis: </strong>${c.explanation}
                    </div>

                    <!-- Suggested Resolution Action -->
                    <div class="flex items-center justify-between pt-2 border-t border-slate-800">
                        <span class="text-xs text-slate-400 italic">Recommended: ${c.action}</span>
                        <div class="flex items-center gap-2">
                            <button onclick="resolveConflictDemo(${c.id_a}, ${c.id_b})" class="px-3 py-1.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-xs font-semibold">
                                Supersede & Resolve
                            </button>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        lucide.createIcons();
    } catch (err) {
        console.error("Conflict scan failed:", err);
    }
}

function testConflictDemo() {
    switchTab('import-chat');
    document.getElementById('sample-scenario-select').value = 'conflict_office';
    loadSampleScenario();
}

async function resolveConflictDemo(idA, idB) {
    if (confirm("Mark the older decision as SUPERSEDED and establish the newer decision as the authoritative company policy?")) {
        try {
            await fetch(`/api/decisions/${idA}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'SUPERSEDED' })
            });
            alert("Policy updated: Older decision marked SUPERSEDED. Company memory refreshed!");
            fetchDashboardStats();
            renderConflictsView();
        } catch (err) {
            console.error("Failed to resolve conflict:", err);
        }
    }
}

// -------------------------------------------------------------
// Decision-to-Task Execution Hub
// -------------------------------------------------------------
async function fetchTasks() {
    const statusFilter = document.getElementById('task-filter-status')?.value || 'all';
    try {
        const res = await fetch(`/api/tasks${statusFilter !== 'all' ? `?status=${statusFilter}` : ''}`);
        const data = await res.json();
        cachedTasks = data.items || [];

        renderKanban(cachedTasks);
    } catch (err) {
        console.error("Failed to fetch tasks:", err);
    }
}

function renderKanban(tasks) {
    const pendingCol = document.getElementById('kanban-col-pending');
    const inprogressCol = document.getElementById('kanban-col-inprogress');
    const completedCol = document.getElementById('kanban-col-completed');

    if (!pendingCol || !inprogressCol || !completedCol) return;

    const pending = tasks.filter(t => t.status === 'PENDING');
    const inprogress = tasks.filter(t => t.status === 'IN_PROGRESS');
    const completed = tasks.filter(t => t.status === 'COMPLETED');

    document.getElementById('kanban-count-pending').textContent = pending.length;
    document.getElementById('kanban-count-inprogress').textContent = inprogress.length;
    document.getElementById('kanban-count-completed').textContent = completed.length;

    pendingCol.innerHTML = pending.length ? pending.map(renderTaskCardHtml).join('') : `<p class="text-slate-600 text-xs py-8 text-center italic">No pending tasks</p>`;
    inprogressCol.innerHTML = inprogress.length ? inprogress.map(renderTaskCardHtml).join('') : `<p class="text-slate-600 text-xs py-8 text-center italic">No tasks in progress</p>`;
    completedCol.innerHTML = completed.length ? completed.map(renderTaskCardHtml).join('') : `<p class="text-slate-600 text-xs py-8 text-center italic">No completed tasks</p>`;

    lucide.createIcons();
}

function renderTaskCardHtml(t) {
    const priorityColor = {
        'HIGH': 'text-rose-400 bg-rose-500/10 border-rose-500/20',
        'MEDIUM': 'text-amber-400 bg-amber-500/10 border-amber-500/20',
        'LOW': 'text-slate-400 bg-slate-500/10 border-slate-500/20'
    }[t.priority] || 'text-slate-400';

    return `
        <div class="bg-slate-800/70 border border-slate-700 rounded-xl p-3 space-y-2.5 text-xs shadow-sm hover:border-slate-600 transition-colors">
            <div class="flex items-center justify-between gap-1">
                <span class="font-mono text-[10px] text-brand-300 bg-brand-500/10 px-1.5 py-0.5 rounded cursor-pointer" onclick="openDecisionDetail(${t.decision_id})">
                    ${t.decision_code || 'DEC'}
                </span>
                <span class="text-[10px] font-semibold px-1.5 py-0.5 rounded border ${priorityColor}">
                    ${t.priority}
                </span>
            </div>

            <p class="font-medium text-slate-200 leading-snug">${t.title}</p>

            <div class="pt-2 border-t border-slate-700/60 flex items-center justify-between text-[11px] text-slate-400">
                <span class="flex items-center gap-1">
                    <i data-lucide="user" class="w-3 h-3 text-slate-500"></i> ${t.assignee}
                </span>
                <span class="font-mono text-[10px] ${t.due_date && new Date(t.due_date) < new Date() && t.status !== 'COMPLETED' ? 'text-rose-400 font-bold' : ''}">
                    ${t.due_date || 'No deadline'}
                </span>
            </div>

            <!-- Fast Status Switch Buttons -->
            <div class="flex items-center justify-end gap-1 pt-1">
                ${t.status !== 'PENDING' ? `
                    <button onclick="toggleTaskStatus(${t.id}, 'PENDING')" class="text-[10px] px-2 py-0.5 rounded bg-slate-700 hover:bg-slate-600 text-slate-300">
                        Pending
                    </button>
                ` : ''}
                ${t.status !== 'IN_PROGRESS' ? `
                    <button onclick="toggleTaskStatus(${t.id}, 'IN_PROGRESS')" class="text-[10px] px-2 py-0.5 rounded bg-blue-600/20 hover:bg-blue-600/30 text-blue-300">
                        Start
                    </button>
                ` : ''}
                ${t.status !== 'COMPLETED' ? `
                    <button onclick="toggleTaskStatus(${t.id}, 'COMPLETED')" class="text-[10px] px-2 py-0.5 rounded bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300">
                        Complete
                    </button>
                ` : ''}
            </div>
        </div>
    `;
}

async function toggleTaskStatus(taskId, newStatus) {
    try {
        await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        fetchTasks();
        fetchDashboardStats();
    } catch (err) {
        console.error("Failed to update task status:", err);
    }
}

async function quickAddTask(decisionId, title, defaultAssignee) {
    try {
        await fetch(`/api/tasks?decision_id=${decisionId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                assignee: defaultAssignee || 'Unassigned',
                priority: 'MEDIUM',
                status: 'PENDING'
            })
        });
        openDecisionDetail(decisionId);
        fetchTasks();
        fetchDashboardStats();
    } catch (err) {
        console.error("Failed to add task:", err);
    }
}

// -------------------------------------------------------------
// Outcome Tracking & Retrospectives ("Did it work?")
// -------------------------------------------------------------
async function renderOutcomesView() {
    const container = document.getElementById('outcomes-table-container');
    if (!container) return;

    if (!cachedDecisions.length) await fetchDecisions();

    container.innerHTML = cachedDecisions.map(d => {
        const outcomeBadge = {
            'SUCCESS': '<span class="text-xs font-bold px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">✓ SUCCESS</span>',
            'PARTIAL_SUCCESS': '<span class="text-xs font-bold px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">~ PARTIAL SUCCESS</span>',
            'FAILED': '<span class="text-xs font-bold px-2.5 py-1 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">✕ FAILED</span>',
            'PENDING_EVALUATION': '<span class="text-xs font-medium px-2.5 py-1 rounded-full bg-slate-800 text-slate-400 border border-slate-700">⏳ Pending Review</span>'
        }[d.outcome_status] || '';

        return `
            <div class="bg-slate-900 border border-slate-800 rounded-2xl p-5 space-y-3">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="text-xs font-mono font-bold text-brand-300 bg-brand-500/10 px-2 py-0.5 rounded">${d.decision_code}</span>
                        <h3 class="text-sm font-bold text-white">${d.title}</h3>
                    </div>
                    ${outcomeBadge}
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div class="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                        <span class="text-[11px] font-semibold text-slate-400 block mb-0.5">Target Expected KPI:</span>
                        <p class="text-slate-300 italic">${d.expected_outcome || 'No explicit KPI logged'}</p>
                    </div>

                    <div class="bg-slate-800/40 p-3 rounded-xl border border-slate-800">
                        <span class="text-[11px] font-semibold text-slate-400 block mb-0.5">Retrospective Findings / Results:</span>
                        <p class="text-slate-200">${d.outcome_notes || 'Pending evaluation by project owner'}</p>
                    </div>
                </div>

                ${d.lessons_learned ? `
                    <div class="bg-amber-500/10 border border-amber-500/20 p-2.5 rounded-xl text-xs text-amber-200 flex items-start gap-2">
                        <i data-lucide="lightbulb" class="w-4 h-4 text-amber-400 mt-0.5 shrink-0"></i>
                        <div>
                            <span class="font-bold">Post-Mortem Lessons Learned: </span>${d.lessons_learned}
                        </div>
                    </div>
                ` : ''}

                <div class="flex items-center justify-between pt-2 border-t border-slate-800/80 text-xs">
                    <span class="text-slate-500 text-[11px]">Owner: ${d.owner_name} | Target: ${d.deadline_date || 'N/A'}</span>
                    <button onclick="openOutcomeModal(${d.id})" class="px-3 py-1.5 rounded-xl bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-semibold border border-amber-500/30 flex items-center gap-1.5 transition-all">
                        <i data-lucide="edit-3" class="w-3.5 h-3.5"></i>
                        <span>${d.outcome_status === 'PENDING_EVALUATION' ? 'Evaluate Outcome' : 'Edit Outcome'}</span>
                    </button>
                </div>
            </div>
        `;
    }).join('');

    lucide.createIcons();
}

function openOutcomeModal(id) {
    const d = cachedDecisions.find(x => x.id === id);
    if (!d) return;

    document.getElementById('eval-decision-id').value = d.id;
    document.getElementById('eval-status').value = d.outcome_status !== 'PENDING_EVALUATION' ? d.outcome_status : 'SUCCESS';
    document.getElementById('eval-notes').value = d.outcome_notes || '';
    document.getElementById('eval-lessons').value = d.lessons_learned || '';
    document.getElementById('eval-by').value = d.outcome_evaluated_by || 'Management';

    openModal('modal-outcome-eval');
}

async function submitOutcomeEvaluation() {
    const id = document.getElementById('eval-decision-id').value;
    const payload = {
        outcome_status: document.getElementById('eval-status').value,
        outcome_notes: document.getElementById('eval-notes').value,
        lessons_learned: document.getElementById('eval-lessons').value,
        evaluated_by: document.getElementById('eval-by').value
    };

    try {
        await fetch(`/api/decisions/${id}/outcome`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        closeModal('modal-outcome-eval');
        alert("Retrospective outcome recorded successfully!");
        fetchDecisions();
        fetchDashboardStats();
    } catch (err) {
        console.error("Failed to record outcome:", err);
        alert("Error: " + err.message);
    }
}

// -------------------------------------------------------------
// Ask Memory AI (Natural Language Q&A)
// -------------------------------------------------------------
function setQueryAndAsk(q) {
    document.getElementById('ask-memory-input').value = q;
    submitAskMemory();
}

async function submitAskMemory() {
    const query = document.getElementById('ask-memory-input').value.trim();
    if (!query) return;

    const respContainer = document.getElementById('ask-response-container');
    const mdContainer = document.getElementById('ask-response-markdown');
    const insightsList = document.getElementById('ask-insights-list');

    respContainer.classList.remove('hidden');
    mdContainer.innerHTML = `<div class="flex items-center gap-2 text-slate-400 py-4"><i data-lucide="loader-2" class="w-4 h-4 animate-spin text-amber-400"></i> Searching Decision Memory Vault & synthesizing answer...</div>`;
    insightsList.innerHTML = '';
    lucide.createIcons();

    try {
        const res = await fetch('/api/decisions/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await res.json();

        // Convert simple markdown to html
        let html = data.answer
            .replace(/^### (.*$)/gim, '<h4 class="text-sm font-bold text-amber-300 mt-2">$1</h4>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/^> (.*$)/gim, '<blockquote class="border-l-2 border-amber-500 pl-3 py-1 my-2 text-slate-300 bg-slate-950 rounded-r">$1</blockquote>')
            .replace(/\n\n/g, '<br><br>');

        mdContainer.innerHTML = html;
        document.getElementById('ask-citations-count').textContent = `${data.relevant_decisions.length} Precedent(s) Found`;

        if (data.synthesized_insights && data.synthesized_insights.length) {
            insightsList.innerHTML = data.synthesized_insights.map(ins => `
                <div class="flex items-start gap-2">
                    <span class="text-amber-400 mt-0.5">•</span>
                    <span>${ins}</span>
                </div>
            `).join('');
        }
        lucide.createIcons();
    } catch (err) {
        console.error("Ask Memory failed:", err);
        mdContainer.innerHTML = `<p class="text-rose-400">Error querying Decision Memory: ${err.message}</p>`;
    }
}

// -------------------------------------------------------------
// WhatsApp Broadcast Export
// -------------------------------------------------------------
async function exportWhatsApp(id) {
    try {
        const res = await fetch(`/api/decisions/${id}/export-whatsapp`);
        const data = await res.json();
        document.getElementById('whatsapp-formatted-text').value = data.text;
        openModal('modal-whatsapp-export');
    } catch (err) {
        console.error("Failed to export WhatsApp:", err);
    }
}

function copyWhatsAppToClipboard() {
    const text = document.getElementById('whatsapp-formatted-text');
    text.select();
    navigator.clipboard.writeText(text.value);

    const msg = document.getElementById('copy-confirm-msg');
    msg.classList.remove('opacity-0');
    setTimeout(() => {
        msg.classList.add('opacity-0');
    }, 2000);
}

// -------------------------------------------------------------
// Manual New Decision Logging
// -------------------------------------------------------------
function openNewDecisionModal() {
    openModal('modal-new-decision');
}

async function submitManualDecision() {
    const title = document.getElementById('manual-title').value.trim();
    const dept = document.getElementById('manual-department').value;
    const owner = document.getElementById('manual-owner').value.trim();
    const problem = document.getElementById('manual-problem').value.trim();
    const decision = document.getElementById('manual-decision').value.trim();
    const reasoning = document.getElementById('manual-reasoning').value.trim();
    const deadline = document.getElementById('manual-deadline').value;
    const budget = document.getElementById('manual-budget').value.trim();
    const expected = document.getElementById('manual-expected').value.trim();

    if (!title || !owner || !problem || !decision || !reasoning) {
        alert("Please fill in all required fields (Title, Owner, Problem, Decision, and Reasoning)!");
        return;
    }

    const payload = {
        title: title,
        department: dept,
        category: "Strategy",
        problem_context: problem,
        decision_text: decision,
        reasoning: reasoning,
        rejected_alternatives: [],
        owner_name: owner,
        owner_role: "Lead",
        participants: [owner],
        source_type: "direct",
        deadline_date: deadline || null,
        budget_or_cost: budget,
        status: "ACTIVE",
        expected_outcome: expected,
        outcome_status: "PENDING_EVALUATION",
        tags: [dept.toLowerCase()]
    };

    try {
        const res = await fetch('/api/decisions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (result.success) {
            closeModal('modal-new-decision');
            alert(`Decision logged as ${result.decision.decision_code}!`);
            fetchDecisions();
            fetchDashboardStats();
        }
    } catch (err) {
        console.error("Failed to save manual decision:", err);
        alert("Error saving decision: " + err.message);
    }
}

// -------------------------------------------------------------
// Reset Demo Data
// -------------------------------------------------------------
async function resetDemoData() {
    if (confirm("Reset DecisionMemory database back to initial sample business decisions?")) {
        try {
            const res = await fetch('/api/system/reset-demo', { method: 'POST' });
            const data = await res.json();
            alert("Sample business decisions and tasks restored!");
            initApp();
        } catch (err) {
            console.error("Failed to reset demo data:", err);
        }
    }
}

// -------------------------------------------------------------
// Modal Utilities
// -------------------------------------------------------------
function openModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.remove('hidden');
}

function closeModal(modalId) {
    const el = document.getElementById(modalId);
    if (el) el.classList.add('hidden');
}

function closeAllModals() {
    document.querySelectorAll('.modal-backdrop').forEach(m => m.classList.add('hidden'));
}
