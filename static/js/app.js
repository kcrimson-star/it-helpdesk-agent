/**
 * NovaDesk AI — Enterprise Helpdesk SPA Controller
 */

// Global App State
const state = {
  activeTab: 'chat',
  chatHistory: [],
  currentDiagnosis: null,
  currentTicketId: null,
  lastTriageAnalysis: null,
  lastTriageFormData: null,
  sessionId: 'sess-' + Math.random().toString(36).substring(2, 9),
  searchDebounceTimer: null,
  kbDebounceTimer: null,
};

// API Base calculation: if opened as file:// or without host, default to http://localhost:8000
const API_BASE = (window.location.protocol === 'file:' || !window.location.host) ? 'http://localhost:8000' : '';

async function apiFetch(endpoint, options = {}, retries = 1) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  try {
    return await fetch(url, options);
  } catch (err) {
    if (retries > 0) {
      await new Promise(r => setTimeout(r, 600));
      return await apiFetch(endpoint, options, retries - 1);
    }
    throw err;
  }
}

// On Page Load
document.addEventListener('DOMContentLoaded', () => {
  loadStats();
  loadTickets();
  loadKB();
  lucide.createIcons();
});

// Toast System
function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  
  let bg = 'bg-slate-800 border-slate-700 text-slate-200';
  let icon = 'info';
  if (type === 'success') {
    bg = 'bg-emerald-950 border-emerald-800 text-emerald-200';
    icon = 'check-circle';
  } else if (type === 'error') {
    bg = 'bg-red-950 border-red-800 text-red-200';
    icon = 'alert-octagon';
  } else if (type === 'warning') {
    bg = 'bg-amber-950 border-amber-800 text-amber-200';
    icon = 'alert-triangle';
  }

  toast.className = `toast-enter flex items-center space-x-2.5 px-4 py-3 rounded-xl border shadow-xl text-xs ${bg}`;
  toast.innerHTML = `
    <i data-lucide="${icon}" class="w-4 h-4 flex-shrink-0"></i>
    <span class="font-medium">${message}</span>
  `;
  container.appendChild(toast);
  lucide.createIcons();

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Tab Switching
function switchTab(tabId) {
  state.activeTab = tabId;

  // Update Tab buttons
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('border-blue-500', 'text-blue-400', 'font-semibold');
    btn.classList.add('border-transparent', 'text-slate-400');
  });

  const activeBtn = document.getElementById(`tab-btn-${tabId}`);
  if (activeBtn) {
    activeBtn.classList.add('border-blue-500', 'text-blue-400', 'font-semibold');
    activeBtn.classList.remove('border-transparent', 'text-slate-400');
  }

  // Update content visibility
  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.add('hidden');
  });

  const activeContent = document.getElementById(`tab-content-${tabId}`);
  if (activeContent) {
    activeContent.classList.remove('hidden');
  }

  if (tabId === 'tickets') {
    loadTickets();
    loadStats();
  } else if (tabId === 'kb') {
    loadKB();
  }

  lucide.createIcons();
}

// -------------------------------------------------------------
// CHAT & LIVE TRIAGE
// -------------------------------------------------------------

function handleChatKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    document.getElementById('chat-form').dispatchEvent(new Event('submit'));
  }
}

async function handleChatSubmit(e) {
  e.preventDefault();
  const input = document.getElementById('chat-input');
  const message = input.value.trim();
  if (!message) return;

  // Add user bubble
  appendChatMessage('user', message);
  input.value = '';
  input.disabled = true;
  document.getElementById('chat-send-btn').disabled = true;

  // Show thinking indicator
  const thinkingId = appendChatThinking();

  try {
    const res = await apiFetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        session_id: state.sessionId,
        message: message,
        history: state.chatHistory.map(m => ({ role: m.role, content: m.content }))
      })
    });

    removeChatThinking(thinkingId);

    if (!res.ok) {
      const errData = await res.json().catch(() => null);
      let msg = `Server returned HTTP ${res.status}`;
      if (errData && errData.detail) msg = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      throw new Error(msg);
    }

    const data = await res.json();
    appendChatMessage('assistant', data.reply);

    // Save to history
    state.chatHistory.push({ role: 'user', content: message });
    state.chatHistory.push({ role: 'assistant', content: data.reply });

    // Update diagnosis card if present
    if (data.diagnosis) {
      state.currentDiagnosis = data.diagnosis;
      renderDiagnosisCard(data.diagnosis);
    }

    // Render quick replies
    renderChatQuickReplies(data.suggested_quick_replies);

  } catch (err) {
    removeChatThinking(thinkingId);
    console.error('Chat error:', err);
    let errorDetail = err.message || '';
    let suggestion = '';
    if (errorDetail.toLowerCase().includes('network') || errorDetail.toLowerCase().includes('failed to fetch')) {
      suggestion = `<br><br>💡 **Connection tip:** Please ensure you are viewing NovaDesk directly at <a href="http://localhost:8000" target="_blank" class="underline text-blue-400 font-semibold">http://localhost:8000</a> and that the server is running with <code>python run.py</code>.`;
    }
    appendChatMessage('assistant', `⚠️ **Troubleshooting service notice:** ${errorDetail}.${suggestion}`);
    showToast('Failed to contact helpdesk agent', 'error');
  } finally {
    input.disabled = false;
    document.getElementById('chat-send-btn').disabled = false;
    input.focus();
    lucide.createIcons();
  }
}

function sendQuickPrompt(promptText) {
  const input = document.getElementById('chat-input');
  input.value = promptText;
  document.getElementById('chat-form').dispatchEvent(new Event('submit'));
}

function clearChatHistory() {
  state.chatHistory = [];
  state.currentDiagnosis = null;
  state.sessionId = 'sess-' + Math.random().toString(36).substring(2, 9);
  
  const container = document.getElementById('chat-messages');
  container.innerHTML = `
    <div class="flex items-start space-x-3">
      <div class="w-8 h-8 rounded-full bg-blue-600/20 border border-blue-500/40 flex-shrink-0 flex items-center justify-center text-blue-400">
        <i data-lucide="bot" class="w-4 h-4"></i>
      </div>
      <div class="bg-slate-800/80 border border-slate-700/60 rounded-2xl rounded-tl-sm p-4 text-xs max-w-[85%] text-slate-200 prose-dark">
        <p class="font-semibold text-blue-400 mb-1">Session Reset.</p>
        <p>I'm ready to assist with a new incident or question. Describe the problem symptoms or error code below.</p>
      </div>
    </div>
  `;

  // Reset diagnosis card
  document.getElementById('diag-empty-state').classList.remove('hidden');
  document.getElementById('diag-content').classList.add('hidden');
  document.getElementById('diag-badge-status').textContent = 'Awaiting Input';
  document.getElementById('chat-quick-replies').classList.add('hidden');

  lucide.createIcons();
  showToast('Chat history cleared', 'info');
}

function appendChatMessage(role, content) {
  const container = document.getElementById('chat-messages');
  const isUser = role === 'user';
  const bubble = document.createElement('div');
  bubble.className = `flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`;

  const iconMarkup = isUser
    ? `<div class="w-8 h-8 rounded-full bg-slate-700 border border-slate-600 flex-shrink-0 flex items-center justify-center text-slate-200"><i data-lucide="user" class="w-4 h-4"></i></div>`
    : `<div class="w-8 h-8 rounded-full bg-blue-600/20 border border-blue-500/40 flex-shrink-0 flex items-center justify-center text-blue-400"><i data-lucide="bot" class="w-4 h-4"></i></div>`;

  const bubbleBg = isUser
    ? 'bg-blue-600 text-white rounded-tr-sm'
    : 'bg-slate-800/90 border border-slate-700/70 text-slate-200 rounded-tl-sm';

  const htmlContent = isUser ? escapeHtml(content) : marked.parse(content);

  bubble.innerHTML = `
    ${iconMarkup}
    <div class="${bubbleBg} rounded-2xl p-4 text-xs max-w-[85%] prose-dark shadow-md break-words">
      ${htmlContent}
    </div>
  `;

  container.appendChild(bubble);
  container.scrollTop = container.scrollHeight;
  lucide.createIcons();
}

function appendChatThinking() {
  const container = document.getElementById('chat-messages');
  const id = 'thinking-' + Date.now();
  const el = document.createElement('div');
  el.id = id;
  el.className = 'flex items-start space-x-3';
  el.innerHTML = `
    <div class="w-8 h-8 rounded-full bg-blue-600/20 border border-blue-500/40 flex-shrink-0 flex items-center justify-center text-blue-400">
      <i data-lucide="bot" class="w-4 h-4"></i>
    </div>
    <div class="bg-slate-800 border border-slate-700/60 rounded-2xl rounded-tl-sm px-4 py-3 text-xs text-slate-400 flex items-center space-x-2">
      <div class="flex space-x-1">
        <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
        <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
        <span class="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
      </div>
      <span class="text-[11px] font-medium text-slate-400">Diagnosing issue with gpt-oss-120b...</span>
    </div>
  `;
  container.appendChild(el);
  container.scrollTop = container.scrollHeight;
  lucide.createIcons();
  return id;
}

function removeChatThinking(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function renderChatQuickReplies(replies) {
  const container = document.getElementById('chat-quick-replies');
  if (!replies || replies.length === 0) {
    container.classList.add('hidden');
    return;
  }

  container.innerHTML = '';
  replies.forEach(r => {
    const btn = document.createElement('button');
    btn.className = 'px-3 py-1 rounded-full bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 text-[11px] transition';
    btn.textContent = r;
    btn.onclick = () => {
      if (r.toLowerCase().includes('create a ticket')) {
        createTicketFromDiagnosis();
      } else {
        sendQuickPrompt(r);
      }
    };
    container.appendChild(btn);
  });
  container.classList.remove('hidden');
}

function renderDiagnosisCard(diag) {
  if (!diag) return;

  document.getElementById('diag-empty-state').classList.add('hidden');
  document.getElementById('diag-content').classList.remove('hidden');
  
  const statusBadge = document.getElementById('diag-badge-status');
  statusBadge.textContent = 'Diagnosed';
  statusBadge.className = 'px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30';

  document.getElementById('diag-title').textContent = diag.title || 'Technical Inquiry';
  document.getElementById('diag-category').innerHTML = `<i data-lucide="tag" class="w-3 h-3 mr-1"></i> ${diag.category}`;
  
  // Priority styling
  const prioEl = document.getElementById('diag-priority');
  let prioColor = 'text-blue-400';
  if (diag.priority === 'Critical') prioColor = 'text-red-400 font-bold';
  else if (diag.priority === 'High') prioColor = 'text-amber-400 font-semibold';
  prioEl.className = `font-medium flex items-center mt-0.5 ${prioColor}`;
  prioEl.innerHTML = `<i data-lucide="alert-triangle" class="w-3 h-3 mr-1"></i> ${diag.priority} (P${getPrioNumber(diag.priority)})`;

  document.getElementById('diag-sla').innerHTML = `<i data-lucide="clock" class="w-3 h-3 mr-1"></i> ${diag.estimated_sla_hours}h SLA`;
  document.getElementById('diag-dept').innerHTML = `<i data-lucide="git-pull-request" class="w-3 h-3 mr-1"></i> ${diag.assigned_department || 'Helpdesk'}`;
  document.getElementById('diag-rootcause').textContent = diag.root_cause_hypothesis || 'Determined through symptom evaluation.';

  // Solutions List
  const solList = document.getElementById('diag-solutions-list');
  solList.innerHTML = '';
  (diag.solutions || []).forEach(step => {
    const li = document.createElement('li');
    li.className = 'flex items-start space-x-2 text-[11px] leading-relaxed';
    li.innerHTML = `
      <i data-lucide="check" class="w-3.5 h-3.5 text-blue-400 flex-shrink-0 mt-0.5"></i>
      <span>${escapeHtml(step)}</span>
    `;
    solList.appendChild(li);
  });

  // Commands List
  const cmdContainer = document.getElementById('diag-commands-container');
  const cmdList = document.getElementById('diag-commands-list');
  cmdList.innerHTML = '';
  if (diag.quick_commands && diag.quick_commands.length > 0) {
    diag.quick_commands.forEach(cmd => {
      const box = document.createElement('div');
      box.className = 'flex items-center justify-between p-2 rounded-lg bg-slate-950 border border-slate-800 text-cyan-300';
      box.innerHTML = `
        <span class="truncate mr-2">${escapeHtml(cmd)}</span>
        <button onclick="copyToClipboard('${escapeHtml(cmd)}')" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] transition">Copy</button>
      `;
      cmdList.appendChild(box);
    });
    cmdContainer.classList.remove('hidden');
  } else {
    cmdContainer.classList.add('hidden');
  }

  lucide.createIcons();
}

function getPrioNumber(prio) {
  if (prio === 'Critical') return 1;
  if (prio === 'High') return 2;
  if (prio === 'Medium') return 3;
  return 4;
}

// -------------------------------------------------------------
// FAST TRIAGE FORM TAB
// -------------------------------------------------------------

function populateSampleTriage() {
  document.getElementById('triage-title').value = 'Outlook Disconnected & Stalled Outbox';
  document.getElementById('triage-system-info').value = 'Windows 11 Enterprise 23H2, Outlook 365 Cached Mode';
  document.getElementById('triage-description').value = 'Outlook shows Disconnected in status bar. 4 customer emails are stuck in Outbox and will not send. User already restarted Outlook once. System time is accurate.';
  document.getElementById('triage-department').value = 'Operations';
  showToast('Sample scenario inserted', 'info');
}

async function handleTriageSubmit(e) {
  e.preventDefault();
  const desc = document.getElementById('triage-description').value.trim();
  if (!desc) return;

  const title = document.getElementById('triage-title').value.trim();
  const requester = document.getElementById('triage-requester-name').value.trim();
  const email = document.getElementById('triage-requester-email').value.trim();
  const dept = document.getElementById('triage-department').value;
  const sysInfo = document.getElementById('triage-system-info').value.trim();

  const submitBtn = document.getElementById('triage-submit-btn');
  submitBtn.disabled = true;
  submitBtn.innerHTML = `<span class="w-3.5 h-3.5 border-2 border-white/20 border-t-white rounded-full animate-spin mr-2"></span> Analyzing with Groq...`;

  try {
    const res = await apiFetch('/api/triage/classify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        issue_description: desc,
        title: title || undefined,
        requester_name: requester,
        requester_email: email,
        system_info: sysInfo || undefined
      })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderTriageResult(data.analysis, data.relevant_kb_articles, {
      title, desc, requester, email, dept
    });
    showToast('AI Triage completed successfully', 'success');

  } catch (err) {
    showToast(`Triage error: ${err.message}`, 'error');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<i data-lucide="sparkles" class="w-4 h-4 mr-2"></i><span>Run AI Triage Analysis</span>`;
    lucide.createIcons();
  }
}

function renderTriageResult(analysis, kbArticles, formData) {
  state.lastTriageAnalysis = analysis;
  state.lastTriageFormData = formData;

  const container = document.getElementById('triage-result-card');
  container.classList.remove('hidden');

  let kbMarkup = '';
  if (kbArticles && kbArticles.length > 0) {
    kbMarkup = `
      <div class="mt-4 pt-4 border-t border-slate-800">
        <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-2">Relevant Internal Runbooks (Knowledge Base)</span>
        <div class="space-y-2">
          ${kbArticles.map(kb => `
            <div class="p-3 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs">
              <div>
                <span class="font-semibold text-white block">${escapeHtml(kb.title)}</span>
                <span class="text-[11px] text-slate-400">${escapeHtml(kb.summary)}</span>
              </div>
              <button onclick="switchTab('kb')" class="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-blue-400 text-xs whitespace-nowrap ml-3">View SOP</button>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  let commandsMarkup = '';
  if (analysis.quick_commands && analysis.quick_commands.length > 0) {
    commandsMarkup = `
      <div class="mt-4 pt-4 border-t border-slate-800">
        <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-2">Diagnostic Terminal Commands</span>
        <div class="space-y-1.5 font-mono text-[11px]">
          ${analysis.quick_commands.map(cmd => `
            <div class="flex items-center justify-between p-2 rounded-lg bg-slate-950 border border-slate-800 text-cyan-300">
              <span class="truncate mr-2">${escapeHtml(cmd)}</span>
              <button onclick="copyToClipboard('${escapeHtml(cmd)}')" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] transition">Copy</button>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  container.innerHTML = `
    <div class="flex items-center justify-between pb-4 border-b border-slate-800">
      <div>
        <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">AI Incident Analysis</span>
        <h3 class="text-base font-bold text-white mt-1">${escapeHtml(analysis.title)}</h3>
      </div>
      <button onclick="handleCreateTicketFromTriage()" class="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs flex items-center space-x-1.5 shadow-md shadow-emerald-600/30 transition">
        <i data-lucide="check" class="w-4 h-4"></i>
        <span>Create Official Ticket</span>
      </button>
    </div>

    <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
      <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
        <span class="text-[10px] text-slate-500 block">Classified Category</span>
        <span class="font-semibold text-blue-400 block mt-0.5">${escapeHtml(analysis.category)}</span>
      </div>
      <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
        <span class="text-[10px] text-slate-500 block">Calculated Priority</span>
        <span class="font-semibold ${analysis.priority === 'Critical' ? 'text-red-400 font-bold' : 'text-amber-400'} block mt-0.5">${escapeHtml(analysis.priority)} (P${getPrioNumber(analysis.priority)})</span>
      </div>
      <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
        <span class="text-[10px] text-slate-500 block">SLA Target</span>
        <span class="font-semibold text-emerald-400 block mt-0.5">${analysis.estimated_sla_hours} Hours</span>
      </div>
      <div class="p-3 rounded-xl bg-slate-950 border border-slate-800">
        <span class="text-[10px] text-slate-500 block">Target Support Team</span>
        <span class="font-semibold text-purple-400 block mt-0.5">${escapeHtml(analysis.assigned_department)}</span>
      </div>
    </div>

    <div class="p-3.5 rounded-xl bg-blue-950/30 border border-blue-900/40 text-xs">
      <span class="text-[10px] uppercase font-bold tracking-wider text-blue-400 block mb-1">Root Cause Hypothesis</span>
      <p class="text-slate-300 leading-relaxed">${escapeHtml(analysis.root_cause_hypothesis)}</p>
    </div>

    <div>
      <span class="text-[10px] uppercase font-bold tracking-wider text-slate-400 block mb-2">Step-by-Step Resolution Procedures</span>
      <ul class="space-y-1.5 text-xs text-slate-300">
        ${(analysis.solutions || []).map(s => `
          <li class="flex items-start space-x-2">
            <i data-lucide="check-circle-2" class="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5"></i>
            <span>${escapeHtml(s)}</span>
          </li>
        `).join('')}
      </ul>
    </div>

    ${commandsMarkup}
    ${kbMarkup}
  `;

  lucide.createIcons();
  container.scrollIntoView({ behavior: 'smooth' });
}

async function handleCreateTicketFromTriage() {
  if (!state.lastTriageAnalysis || !state.lastTriageFormData) {
    showToast('Triage analysis data missing. Please re-run analysis.', 'error');
    return;
  }
  await createTicketDirectlyFromTriage(state.lastTriageAnalysis, state.lastTriageFormData);
}

async function createTicketDirectlyFromTriage(analysis, formData) {
  try {
    const payload = {
      title: analysis.title || formData.title || 'IT Helpdesk Ticket',
      description: formData.desc,
      category: analysis.category || undefined,
      sub_category: analysis.sub_category || undefined,
      priority: analysis.priority || undefined,
      requester_name: formData.requester || 'Employee',
      requester_email: formData.email || 'employee@company.local',
      department: formData.dept || 'Operations',
      auto_diagnose: false,
      ai_analysis: analysis
    };

    const res = await apiFetch('/api/tickets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      let errMsg = `HTTP ${res.status}`;
      if (errJson && errJson.detail) {
        errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
      throw new Error(errMsg);
    }

    const ticket = await res.json();
    showToast(`Ticket #${ticket.ticket_code} created successfully!`, 'success');
    switchTab('tickets');
    loadTickets();
    loadStats();
  } catch (err) {
    console.error('Error creating ticket:', err);
    showToast(`Failed to create ticket: ${err.message}`, 'error');
  }
}

// -------------------------------------------------------------
// TICKETS MANAGEMENT TAB
// -------------------------------------------------------------

function debounceTicketSearch() {
  clearTimeout(state.searchDebounceTimer);
  state.searchDebounceTimer = setTimeout(() => {
    loadTickets();
  }, 300);
}

async function loadTickets() {
  const status = document.getElementById('filter-status')?.value || 'All';
  const priority = document.getElementById('filter-priority')?.value || 'All';
  const category = document.getElementById('filter-category')?.value || 'All';
  const search = document.getElementById('ticket-search-input')?.value.trim() || '';

  const params = new URLSearchParams();
  if (status && status !== 'All') params.append('status', status);
  if (priority && priority !== 'All') params.append('priority', priority);
  if (category && category !== 'All') params.append('category', category);
  if (search) params.append('search', search);

  try {
    const res = await apiFetch(`/api/tickets?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderTicketsTable(data.tickets);
    
    // Update badge in navigation
    const navCount = document.getElementById('nav-ticket-count');
    if (navCount) navCount.textContent = data.total;
  } catch (err) {
    console.error('Failed to load tickets:', err);
    showToast('Failed to load tickets', 'error');
  }
}

function renderTicketsTable(tickets) {
  const tbody = document.getElementById('tickets-table-body');
  const emptyState = document.getElementById('tickets-empty-state');
  if (!tbody) return;

  tbody.innerHTML = '';
  if (!tickets || tickets.length === 0) {
    emptyState.classList.remove('hidden');
    return;
  }
  emptyState.classList.add('hidden');

  tickets.forEach(t => {
    const tr = document.createElement('tr');
    tr.className = 'hover:bg-slate-800/40 transition cursor-pointer';
    tr.onclick = (e) => {
      // Don't trigger if clicked on an action button
      if (e.target.closest('button')) return;
      openTicketDetail(t.id);
    };

    // Priority badge
    let prioBadge = '';
    if (t.priority === 'Critical') {
      prioBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-bold bg-red-500/15 text-red-400 border border-red-500/30 badge-pulse-critical">P1 Critical</span>`;
    } else if (t.priority === 'High') {
      prioBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">P2 High</span>`;
    } else if (t.priority === 'Medium') {
      prioBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-medium bg-blue-500/15 text-blue-400 border border-blue-500/30">P3 Medium</span>`;
    } else {
      prioBadge = `<span class="px-2.5 py-1 rounded-full text-[10px] font-medium bg-slate-700/50 text-slate-300 border border-slate-600/40">P4 Low</span>`;
    }

    // Status badge
    let statusBadge = '';
    if (t.status === 'Open') {
      statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">Open</span>`;
    } else if (t.status === 'In Progress') {
      statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">In Progress</span>`;
    } else if (t.status === 'Resolved') {
      statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Resolved</span>`;
    } else {
      statusBadge = `<span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-700 text-slate-300">${t.status}</span>`;
    }

    // Format SLA
    const slaFormatted = formatSla(t.sla_deadline, t.status);

    tr.innerHTML = `
      <td class="py-3 px-4 font-mono font-bold text-blue-400">${escapeHtml(t.ticket_code)}</td>
      <td class="py-3 px-4 max-w-xs">
        <div class="font-semibold text-white truncate">${escapeHtml(t.title)}</div>
        <div class="flex items-center space-x-1.5 mt-0.5">
          <span class="text-[10px] text-slate-400 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">${escapeHtml(t.category)}</span>
          <span class="text-[10px] text-slate-500">• ${escapeHtml(t.department)}</span>
        </div>
      </td>
      <td class="py-3 px-4">
        <div class="text-white font-medium">${escapeHtml(t.requester_name)}</div>
        <div class="text-[11px] text-slate-400 font-mono">${escapeHtml(t.requester_email)}</div>
      </td>
      <td class="py-3 px-4">${prioBadge}</td>
      <td class="py-3 px-4">${statusBadge}</td>
      <td class="py-3 px-4 font-mono text-[11px]">${slaFormatted}</td>
      <td class="py-3 px-4 text-right space-x-1.5">
        <button onclick="openTicketDetail(${t.id})" title="View Details" class="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition">
          <i data-lucide="eye" class="w-3.5 h-3.5"></i>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  lucide.createIcons();
}

function formatSla(slaIso, status) {
  if (status === 'Resolved' || status === 'Closed') {
    return `<span class="text-slate-500">Completed</span>`;
  }
  if (!slaIso) return `<span class="text-slate-500">--</span>`;

  const deadline = new Date(slaIso);
  const now = new Date();
  const diffMs = deadline - now;
  const diffHours = Math.round(diffMs / (1000 * 60 * 60));

  if (diffMs < 0) {
    return `<span class="text-red-400 font-bold flex items-center"><i data-lucide="alert-circle" class="w-3 h-3 mr-1"></i>Breached</span>`;
  } else if (diffHours <= 2) {
    return `<span class="text-amber-400 font-semibold">${diffHours}h left</span>`;
  } else {
    return `<span class="text-emerald-400">${diffHours}h remaining</span>`;
  }
}

// -------------------------------------------------------------
// TICKET DETAIL MODAL
// -------------------------------------------------------------

async function openTicketDetail(ticketId) {
  state.currentTicketId = ticketId;
  const modal = document.getElementById('modal-ticket-detail');

  try {
    const res = await apiFetch(`/api/tickets/${ticketId}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const t = await res.json();

    document.getElementById('detail-ticket-code').textContent = t.ticket_code;
    document.getElementById('detail-ticket-title').textContent = t.title;
    document.getElementById('detail-ticket-date').textContent = `Created ${new Date(t.created_at).toLocaleString()}`;
    
    document.getElementById('detail-ticket-status-select').value = t.status;
    document.getElementById('detail-ticket-priority-select').value = t.priority;
    document.getElementById('detail-ticket-assignee-select').value = t.assigned_to || 'Tier 1 Helpdesk';
    document.getElementById('detail-ticket-sla').textContent = t.sla_deadline ? new Date(t.sla_deadline).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '--';

    document.getElementById('detail-requester-name').textContent = t.requester_name;
    document.getElementById('detail-requester-dept').textContent = t.department;
    document.getElementById('detail-requester-email').textContent = t.requester_email;
    document.getElementById('detail-ticket-desc').textContent = t.description;

    // Solutions
    const solList = document.getElementById('detail-solutions-list');
    solList.innerHTML = '';
    if (t.solutions && t.solutions.length > 0) {
      t.solutions.forEach(s => {
        const li = document.createElement('li');
        li.className = 'flex items-start space-x-2 text-[11px] leading-relaxed';
        li.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5 text-emerald-400 flex-shrink-0 mt-0.5"></i><span>${escapeHtml(s)}</span>`;
        solList.appendChild(li);
      });
    } else {
      solList.innerHTML = `<li class="text-slate-500 text-[11px]">No automatic solutions generated.</li>`;
    }

    // Commands
    const cmdContainer = document.getElementById('detail-commands-container');
    const cmdList = document.getElementById('detail-commands-list');
    cmdList.innerHTML = '';
    if (t.quick_commands && t.quick_commands.length > 0) {
      t.quick_commands.forEach(cmd => {
        const box = document.createElement('div');
        box.className = 'flex items-center justify-between p-2 rounded-lg bg-slate-950 border border-slate-800 text-cyan-300';
        box.innerHTML = `
          <span class="truncate mr-2">${escapeHtml(cmd)}</span>
          <button onclick="copyToClipboard('${escapeHtml(cmd)}')" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] transition">Copy</button>
        `;
        cmdList.appendChild(box);
      });
      cmdContainer.classList.remove('hidden');
    } else {
      cmdContainer.classList.add('hidden');
    }

    // Resolution box
    const resBox = document.getElementById('detail-resolution-box');
    if (t.resolution_notes) {
      document.getElementById('detail-resolution-notes').textContent = t.resolution_notes;
      resBox.classList.remove('hidden');
    } else {
      resBox.classList.add('hidden');
    }

    // Render Comments Thread
    renderTicketComments(t.comments || []);

    modal.classList.remove('hidden');
    lucide.createIcons();
  } catch (err) {
    showToast(`Failed to load ticket details: ${err.message}`, 'error');
  }
}

function closeTicketDetailModal() {
  document.getElementById('modal-ticket-detail').classList.add('hidden');
  state.currentTicketId = null;
}

function renderTicketComments(comments) {
  const container = document.getElementById('detail-comments-list');
  container.innerHTML = '';
  if (!comments || comments.length === 0) {
    container.innerHTML = `<div class="text-center py-8 text-slate-500 text-xs">No activity logged yet.</div>`;
    return;
  }

  comments.forEach(c => {
    const isSystem = c.author_type === 'system';
    const isAgent = c.author_type === 'agent';
    
    let badgeColor = 'bg-blue-500/20 text-blue-400';
    if (isSystem) badgeColor = 'bg-slate-700 text-slate-300';
    else if (isAgent) badgeColor = 'bg-purple-500/20 text-purple-400';

    const div = document.createElement('div');
    div.className = 'p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs space-y-1';
    div.innerHTML = `
      <div class="flex items-center justify-between text-[10px]">
        <span class="px-1.5 py-0.2 rounded font-semibold ${badgeColor}">${escapeHtml(c.author_name)}</span>
        <span class="text-slate-500 font-mono">${new Date(c.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
      </div>
      <p class="text-slate-300 text-[11px] leading-relaxed">${escapeHtml(c.content)}</p>
    `;
    container.appendChild(div);
  });
  container.scrollTop = container.scrollHeight;
}

async function handleTicketStatusChange() {
  const newStatus = document.getElementById('detail-ticket-status-select').value;
  if (!state.currentTicketId) return;

  try {
    const res = await apiFetch(`/api/tickets/${state.currentTicketId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    showToast(`Status updated to ${newStatus}`, 'success');
    loadTickets();
    loadStats();
  } catch (err) {
    showToast(`Failed to update status: ${err.message}`, 'error');
  }
}

async function handleTicketPriorityChange() {
  const newPrio = document.getElementById('detail-ticket-priority-select').value;
  if (!state.currentTicketId) return;

  try {
    const res = await apiFetch(`/api/tickets/${state.currentTicketId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ priority: newPrio })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    showToast(`Priority updated to ${newPrio}`, 'success');
    loadTickets();
    loadStats();
  } catch (err) {
    showToast(`Failed to update priority: ${err.message}`, 'error');
  }
}

async function handleTicketAssigneeChange() {
  const newAssignee = document.getElementById('detail-ticket-assignee-select').value;
  if (!state.currentTicketId) return;

  try {
    const res = await apiFetch(`/api/tickets/${state.currentTicketId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assigned_to: newAssignee })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    showToast(`Assigned to ${newAssignee}`, 'success');
    loadTickets();
  } catch (err) {
    showToast(`Failed to update assignee: ${err.message}`, 'error');
  }
}

async function handlePostComment(e) {
  e.preventDefault();
  const input = document.getElementById('detail-new-comment');
  const content = input.value.trim();
  if (!content || !state.currentTicketId) return;

  try {
    const res = await apiFetch(`/api/tickets/${state.currentTicketId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        author_name: 'Support Tech',
        author_type: 'agent',
        content: content
      })
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    input.value = '';
    // Reload ticket details
    openTicketDetail(state.currentTicketId);
    showToast('Work note logged', 'info');
  } catch (err) {
    showToast(`Failed to add note: ${err.message}`, 'error');
  }
}

async function openResolvePrompt() {
  if (!state.currentTicketId) return;
  const notes = prompt("Enter resolution summary / root-cause notes:", "Troubleshooting verified and confirmed working with user.");
  if (!notes) return;

  try {
    const res = await apiFetch(`/api/tickets/${state.currentTicketId}/resolve?resolution_notes=${encodeURIComponent(notes)}`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    showToast('Ticket marked as Resolved!', 'success');
    openTicketDetail(state.currentTicketId);
    loadTickets();
    loadStats();
  } catch (err) {
    showToast(`Failed to resolve: ${err.message}`, 'error');
  }
}

async function handleDeleteCurrentTicket() {
  if (!state.currentTicketId) return;
  if (!confirm("Are you sure you want to permanently delete this ticket?")) return;

  try {
    const res = await apiFetch(`/api/tickets/${state.currentTicketId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    showToast('Ticket deleted', 'info');
    closeTicketDetailModal();
    loadTickets();
    loadStats();
  } catch (err) {
    showToast(`Failed to delete: ${err.message}`, 'error');
  }
}

// -------------------------------------------------------------
// CREATE TICKET MODAL WORKFLOW
// -------------------------------------------------------------

function openCreateTicketModal(prefill = null) {
  const modal = document.getElementById('modal-create-ticket');
  modal.classList.remove('hidden');

  if (prefill) {
    document.getElementById('modal-ticket-title').value = prefill.title || '';
    document.getElementById('modal-ticket-desc').value = prefill.description || '';
    document.getElementById('modal-ticket-category').value = prefill.category || '';
    document.getElementById('modal-ticket-priority').value = prefill.priority || '';
    document.getElementById('modal-ticket-requester').value = prefill.requester_name || document.getElementById('modal-ticket-requester').value || 'Marcus Vance';
    document.getElementById('modal-ticket-email').value = prefill.requester_email || document.getElementById('modal-ticket-email').value || 'm.vance@company.corp';
    if (prefill.ai_analysis) {
      document.getElementById('modal-ticket-ai-analysis').value = JSON.stringify(prefill.ai_analysis);
    } else {
      document.getElementById('modal-ticket-ai-analysis').value = '';
    }
  } else {
    document.getElementById('create-ticket-form').reset();
    document.getElementById('modal-ticket-requester').value = 'Marcus Vance';
    document.getElementById('modal-ticket-email').value = 'm.vance@company.corp';
    document.getElementById('modal-ticket-ai-analysis').value = '';
  }

  lucide.createIcons();
}

function closeCreateTicketModal() {
  document.getElementById('modal-create-ticket').classList.add('hidden');
}

function createTicketFromDiagnosis() {
  if (!state.currentDiagnosis) {
    showToast('No active diagnosis available', 'warning');
    return;
  }

  // Last user message as description
  const userMessages = state.chatHistory.filter(m => m.role === 'user');
  const lastDesc = userMessages.length > 0 ? userMessages[userMessages.length - 1].content : state.currentDiagnosis.title;

  openCreateTicketModal({
    title: state.currentDiagnosis.title,
    description: lastDesc,
    category: state.currentDiagnosis.category,
    priority: state.currentDiagnosis.priority,
    ai_analysis: state.currentDiagnosis
  });
}

async function handleCreateTicketSubmit(e) {
  e.preventDefault();
  const desc = document.getElementById('modal-ticket-desc').value.trim();
  if (!desc) {
    showToast('Please provide a problem description', 'warning');
    return;
  }

  const title = document.getElementById('modal-ticket-title').value.trim();
  const requester = document.getElementById('modal-ticket-requester').value.trim() || 'Marcus Vance';
  const email = document.getElementById('modal-ticket-email').value.trim() || 'm.vance@company.corp';
  const category = document.getElementById('modal-ticket-category').value;
  const priority = document.getElementById('modal-ticket-priority').value;
  const analysisRaw = document.getElementById('modal-ticket-ai-analysis').value;

  let aiAnalysis = null;
  if (analysisRaw) {
    try { aiAnalysis = JSON.parse(analysisRaw); } catch (e) {}
  }

  try {
    const payload = {
      title: title || undefined,
      description: desc,
      category: category || undefined,
      priority: priority || undefined,
      requester_name: requester,
      requester_email: email,
      department: 'Operations',
      auto_diagnose: !category || !priority,
      ai_analysis: aiAnalysis
    };

    const res = await apiFetch('/api/tickets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const errJson = await res.json().catch(() => null);
      let errMsg = `HTTP ${res.status}`;
      if (errJson && errJson.detail) {
        errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
      throw new Error(errMsg);
    }

    const ticket = await res.json();
    showToast(`Created ticket #${ticket.ticket_code}!`, 'success');
    closeCreateTicketModal();
    switchTab('tickets');
    loadTickets();
    loadStats();
  } catch (err) {
    console.error('Error creating ticket from modal:', err);
    showToast(`Failed to create ticket: ${err.message}`, 'error');
  }
}

// -------------------------------------------------------------
// KNOWLEDGE BASE TAB
// -------------------------------------------------------------

function debounceKBSearch() {
  clearTimeout(state.kbDebounceTimer);
  state.kbDebounceTimer = setTimeout(() => {
    loadKB();
  }, 250);
}

async function loadKB() {
  const query = document.getElementById('kb-search-input')?.value.trim() || '';
  const params = query ? `?query=${encodeURIComponent(query)}` : '';

  try {
    const res = await apiFetch(`/api/kb${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const articles = await res.json();
    renderKBArticles(articles);
  } catch (err) {
    console.error('KB fetch error:', err);
  }
}

function renderKBArticles(articles) {
  const grid = document.getElementById('kb-grid');
  if (!grid) return;

  grid.innerHTML = '';
  if (!articles || articles.length === 0) {
    grid.innerHTML = `<div class="col-span-2 text-center py-12 text-slate-500 text-xs">No documentation found matching your search.</div>`;
    return;
  }

  articles.forEach(art => {
    const card = document.createElement('div');
    card.className = 'bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-lg space-y-3';
    
    let commandsMarkup = '';
    if (art.quick_commands && art.quick_commands.length > 0) {
      commandsMarkup = `
        <div class="mt-2 pt-2 border-t border-slate-800 space-y-1 font-mono text-[11px]">
          ${art.quick_commands.map(cmd => `
            <div class="flex items-center justify-between p-1.5 rounded bg-slate-950 text-cyan-300">
              <span class="truncate mr-2">${escapeHtml(cmd)}</span>
              <button onclick="copyToClipboard('${escapeHtml(cmd)}')" class="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]">Copy</button>
            </div>
          `).join('')}
        </div>
      `;
    }

    card.innerHTML = `
      <div class="flex items-start justify-between">
        <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">${escapeHtml(art.category)}</span>
        <span class="text-[10px] text-slate-500 font-mono">KB-${art.id}</span>
      </div>
      <h3 class="text-sm font-bold text-white leading-snug">${escapeHtml(art.title)}</h3>
      <p class="text-xs text-slate-400 leading-relaxed">${escapeHtml(art.summary)}</p>
      
      <details class="text-xs text-slate-300 pt-2 border-t border-slate-800">
        <summary class="cursor-pointer text-blue-400 hover:text-blue-300 font-medium py-1 select-none">
          View Standard Operating Procedure (SOP)
        </summary>
        <div class="mt-2 text-[11px] prose-dark bg-slate-950/70 p-3 rounded-xl border border-slate-800">
          ${marked.parse(art.content)}
        </div>
      </details>

      ${commandsMarkup}
    `;
    grid.appendChild(card);
  });

  lucide.createIcons();
}

// -------------------------------------------------------------
// KPI & STATS
// -------------------------------------------------------------

async function loadStats() {
  try {
    const res = await apiFetch('/api/stats');
    if (!res.ok) return;
    const stats = await res.json();

    const elTotal = document.getElementById('kpi-total-tickets');
    const elOpen = document.getElementById('kpi-open-tickets');
    const elCrit = document.getElementById('kpi-critical-tickets');
    const elSla = document.getElementById('kpi-sla-rate');

    if (elTotal) elTotal.textContent = stats.total_tickets;
    if (elOpen) elOpen.textContent = stats.open_tickets + stats.in_progress_tickets;
    if (elCrit) elCrit.textContent = (stats.critical_tickets || 0) + (stats.high_tickets || 0);
    if (elSla) elSla.textContent = `${stats.sla_compliance_rate}%`;

  } catch (err) {
    console.error('Stats error:', err);
  }
}

// -------------------------------------------------------------
// UTILITIES
// -------------------------------------------------------------

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard!', 'info');
  }).catch(() => {
    showToast('Failed to copy', 'error');
  });
}

function copyPreContent(button) {
  const pre = button.previousElementSibling;
  if (pre) {
    copyToClipboard(pre.innerText);
  }
}
