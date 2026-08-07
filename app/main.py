import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.routers import containers, quadlet, commands
from app.routers import systemctl as systemctl_router
from app.routers import services as services_router
from app.routers import auth as auth_router
from app.config import STATIC_DIR, SERVER_HOST, SERVER_PORT, PODMAN_USER, AUTH_ENABLED
from app.auth import auth_middleware, get_current_user

app = FastAPI(title="PodmanPanel")

# Add auth middleware
app.middleware("http")(auth_middleware)

app.include_router(auth_router.router)
app.include_router(containers.router)
app.include_router(quadlet.router)
app.include_router(commands.router)
app.include_router(systemctl_router.router)
app.include_router(services_router.router)


@app.get("/api/info")
def info():
    return {"user": PODMAN_USER, "host": SERVER_HOST, "port": SERVER_PORT}


@app.get("/")
def index(request: Request):
    # If auth enabled and not logged in, show login page
    if AUTH_ENABLED and not get_current_user(request):
        return HTMLResponse(LOGIN_HTML)

    path = Path(STATIC_DIR) / "index.html"
    if path.exists():
        return FileResponse(str(path))
    return HTMLResponse(INDEX_HTML)


@app.get("/static/{filename}")
def static_files(filename: str):
    return FileResponse(os.path.join(STATIC_DIR, filename))


LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - PodmanPanel</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen flex items-center justify-center">
<div class="bg-gray-800 rounded-lg p-8 w-full max-w-md">
    <h1 class="text-2xl font-bold mb-6 text-center">PodmanPanel</h1>
    <form id="login-form" class="space-y-4">
        <div>
            <label for="username" class="block text-sm font-medium mb-1">Username</label>
            <input type="text" id="username" name="username" required
                class="w-full bg-gray-700 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
        </div>
        <div>
            <label for="password" class="block text-sm font-medium mb-1">Password</label>
            <input type="password" id="password" name="password" required
                class="w-full bg-gray-700 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
        </div>
        <div id="error" class="hidden text-red-400 text-sm"></div>
        <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 rounded px-4 py-2 font-medium">
            Login
        </button>
    </form>
</div>

<script>
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorEl = document.getElementById('error');

    try {
        const resp = await fetch('/api/login', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({username, password}),
        });
        const data = await resp.json();

        if (resp.ok) {
            window.location.href = '/';
        } else {
            errorEl.textContent = data.detail || 'Login failed';
            errorEl.classList.remove('hidden');
        }
    } catch (err) {
        errorEl.textContent = 'Connection error';
        errorEl.classList.remove('hidden');
    }
});
</script>
</body>
</html>"""


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PodmanPanel</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-900 text-gray-100 min-h-screen p-6">
<div class="max-w-6xl mx-auto">

    <h1 class="text-3xl font-bold mb-6">
        PodmanPanel
        <span id="podman-user" class="text-sm text-gray-400 font-normal"></span>
    </h1>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

        <!-- Left: unified services list -->
        <div class="lg:col-span-2 space-y-6">
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="flex items-center justify-between mb-3">
                    <h2 class="text-xl font-semibold">Services</h2>
                    <div class="flex gap-2">
                        <button onclick="newQuadlet()" class="text-xs bg-green-700 hover:bg-green-600 px-3 py-1 rounded">+ New Quadlet</button>
                        <button onclick="loadServices()" class="text-xs text-gray-400 hover:text-gray-200">&#x21bb; Refresh</button>
                    </div>
                </div>
                <div class="flex flex-wrap items-center gap-x-4 gap-y-2 mb-3">
                    <input id="filter-search" type="text" placeholder="Szukaj (min. 2 znaki)…"
                        oninput="applyFilters()"
                        class="bg-gray-700 rounded px-3 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-52">
                    <label class="flex items-center gap-2 text-sm cursor-pointer select-none">
                        <input id="filter-running" type="checkbox" checked onchange="applyFilters()"
                            class="w-4 h-4 accent-green-500">
                        Pokaż działające
                    </label>
                    <label class="flex items-center gap-2 text-sm cursor-pointer select-none">
                        <input id="filter-stopped" type="checkbox" onchange="applyFilters()"
                            class="w-4 h-4 accent-gray-400">
                        Pokaż niedziałające
                    </label>
                </div>
                <div id="services" class="space-y-2">
                    <p class="text-gray-400 text-sm">Loading…</p>
                </div>
            </div>
        </div>

        <!-- Right: quick commands + run command -->
        <div class="space-y-6">

            <div class="bg-gray-800 rounded-lg p-4">
                <h2 class="text-xl font-semibold mb-4">Quick Commands</h2>
                <div id="quick-commands" class="space-y-2">
                    <p class="text-gray-400 text-sm">Loading…</p>
                </div>
                <pre id="quick-output" class="mt-3 bg-gray-900 p-3 rounded text-xs overflow-auto max-h-48 hidden"></pre>
            </div>

        </div>
    </div>
</div>

<!-- Edit / Create Modal -->
<div id="edit-modal" class="fixed inset-0 bg-black/80 hidden items-center justify-center z-50">
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 flex flex-col" style="max-height:90vh">
        <h3 id="modal-title" class="text-xl font-semibold mb-1">Edit Quadlet</h3>
        <p id="edit-filename" class="text-gray-400 text-sm mb-3"></p>
        <div id="new-filename-row" class="hidden mb-3">
            <input id="new-filename" type="text" placeholder="myservice.container"
                class="w-full bg-gray-900 px-3 py-2 rounded text-sm font-mono focus:outline-none focus:ring-1 focus:ring-blue-500">
        </div>
        <textarea id="quadlet-editor" rows="20"
            class="flex-1 bg-gray-900 p-3 rounded text-sm font-mono focus:outline-none focus:ring-1 focus:ring-blue-500 overflow-auto"></textarea>
        <div class="flex justify-end gap-2 mt-4">
            <button onclick="closeEditor()" class="px-4 py-2 rounded bg-gray-600 hover:bg-gray-700">Cancel</button>
            <button onclick="saveQuadlet()" class="px-4 py-2 rounded bg-green-600 hover:bg-green-700">Save + daemon-reload</button>
        </div>
    </div>
</div>

<!-- Journal Modal -->
<div id="journal-modal" class="fixed inset-0 bg-black/80 hidden items-center justify-center z-50">
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-4xl mx-4 flex flex-col" style="max-height:90vh">
        <div class="flex items-center justify-between mb-3">
            <div>
                <h3 class="text-xl font-semibold">Journal</h3>
                <p id="journal-service" class="text-gray-400 text-sm"></p>
            </div>
            <div class="flex items-center gap-3">
                <label class="flex items-center gap-2 text-sm cursor-pointer select-none">
                    <input id="journal-follow" type="checkbox" checked
                        class="w-4 h-4 accent-purple-500" onchange="toggleJournalFollow()">
                    Follow
                </label>
                <button onclick="closeJournal()" class="px-3 py-1 rounded bg-gray-600 hover:bg-gray-700 text-sm">Close</button>
            </div>
        </div>
        <div id="journal-output"
            class="flex-1 bg-gray-900 p-3 rounded text-xs font-mono overflow-auto" style="min-height:300px"></div>
    </div>
</div>

<script>
// ── Helpers ───────────────────────────────────────────────────────────────────

function esc(s) {
    return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function stateBadge(state) {
    if (!state) return '<span class="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-400">no container</span>';
    const cls = state === 'running' ? 'bg-green-700' : state === 'paused' ? 'bg-yellow-700' : 'bg-gray-600';
    return `<span class="text-xs px-2 py-0.5 rounded ${cls}">${esc(state)}</span>`;
}

function enabledBadge(enabled) {
    if (!enabled || enabled === 'not-found') return '';
    const cls = enabled === 'enabled'  ? 'bg-blue-800 text-blue-200'
              : enabled === 'disabled' ? 'bg-gray-700 text-gray-400'
              : 'bg-gray-700 text-gray-500';
    return `<span class="text-xs px-2 py-0.5 rounded ${cls}">${esc(enabled)}</span>`;
}

const WILDCARD_IPS = ['', '0.0.0.0', '::', '*'];

function portChips(ports) {
    if (!ports || !ports.length) return '';
    const chips = ports.map(p => {
        const mapping = `${p.host_port ? p.host_port + ':' : ''}${p.container_port}/${p.proto}`;
        // No host port means podman picked a random one — nothing to link to.
        if (!p.host_port || p.proto !== 'tcp') {
            return `<span class="text-xs px-2 py-0.5 rounded bg-gray-800 text-gray-400 font-mono"
                title="${esc(mapping)}">${esc(p.host_port || p.container_port)}</span>`;
        }
        // A port bound to a specific address is only reachable there; otherwise
        // reuse whatever host the panel itself was opened on.
        let host = WILDCARD_IPS.includes(p.host_ip) ? window.location.hostname : p.host_ip;
        if (host.includes(':')) host = `[${host}]`;
        const first = String(p.host_port).split('-')[0];
        const scheme = ['443', '8443'].includes(first) ? 'https' : 'http';
        return `<a href="${scheme}://${host}:${esc(first)}" target="_blank" rel="noopener"
            class="text-xs px-2 py-0.5 rounded bg-gray-800 text-blue-300 hover:bg-blue-900 hover:text-blue-100 font-mono"
            title="${esc(mapping)}">${esc(p.host_port)}</a>`;
    });
    return `<div class="ml-auto flex flex-wrap items-center gap-1">${chips.join('')}</div>`;
}

function toast(msg, ok = true) {
    const t = document.createElement('div');
    t.className = `fixed bottom-5 right-5 px-4 py-2 rounded shadow-lg text-sm z-50 ${ok ? 'bg-green-700' : 'bg-red-700'}`;
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 3500);
}

// ── Info ──────────────────────────────────────────────────────────────────────

async function loadInfo() {
    try {
        const d = await fetch('/api/info').then(r => r.json());
        document.getElementById('podman-user').textContent = 'user: ' + d.user;
    } catch(e) {}
}

// ── Services (unified list) ───────────────────────────────────────────────────

let _services = [];

function _serviceCard(s, i) {
    const name = s.service ? s.service.replace(/\\.service$/, '') : s.container_name;
    const isManaged = !!s.service;

    const meta = [
        s.quadlet_file ? `<span class="text-gray-500 text-xs">${esc(s.quadlet_file)}</span>` : '',
        s.image        ? `<span class="text-gray-400 text-xs truncate">${esc(s.image)}</span>` : '',
    ].filter(Boolean).join(' ');

    const managedBtns = isManaged ? `
        <button onclick="editSvc(${i})"      class="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">Edit</button>
        <button onclick="openJournal(${i})"  class="px-2 py-1 text-xs rounded bg-purple-800 hover:bg-purple-700">Journal</button>
        <button onclick="svcStatus(${i})"    class="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">Status</button>
        <button onclick="svcAction(${i},'start')"   class="px-2 py-1 text-xs rounded bg-green-800 hover:bg-green-700">Start</button>
        <button onclick="svcAction(${i},'stop')"    class="px-2 py-1 text-xs rounded bg-red-800 hover:bg-red-700">Stop</button>
        <button onclick="svcAction(${i},'restart')" class="px-2 py-1 text-xs rounded bg-yellow-800 hover:bg-yellow-700">Restart</button>
        <button onclick="svcAction(${i},'enable')"  class="px-2 py-1 text-xs rounded bg-blue-900 hover:bg-blue-800">Enable</button>
        <button onclick="svcAction(${i},'disable')" class="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600">Disable</button>
    ` : '';

    const podmanBtns = s.container_id ? `
        <button onclick="podmanAction(${i},'${s.state === 'running' ? 'stop' : 'start'}')"
            class="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600">
            ${s.state === 'running' ? 'podman stop' : 'podman start'}
        </button>
        ${!isManaged ? `<button onclick="podmanAction(${i},'restart')" class="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600">Restart</button>` : ''}
        ${s.image ? `<button onclick="pullImage(${i})" class="px-2 py-1 text-xs rounded bg-blue-900 hover:bg-blue-800">Pull</button>` : ''}
    ` : '';

    return `
    <div class="bg-gray-700 rounded p-3">
        <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mb-2">
            <span class="font-medium">${esc(name)}</span>
            ${meta}
            ${stateBadge(s.state)}
            ${enabledBadge(s.enabled)}
            ${portChips(s.ports)}
        </div>
        <div class="flex flex-wrap gap-1">
            ${managedBtns}
            ${podmanBtns}
        </div>
        <div id="svc-out-${i}" class="hidden mt-2">
            <pre class="bg-gray-900 p-2 rounded text-xs overflow-auto max-h-48 whitespace-pre-wrap"></pre>
        </div>
    </div>`;
}

function applyFilters() {
    const query = document.getElementById('filter-search').value;
    const showRunning = document.getElementById('filter-running').checked;
    const showStopped = document.getElementById('filter-stopped').checked;
    const needle = query.length >= 2 ? query.toLowerCase() : '';

    const visible = _services.map((s, i) => ({ s, i })).filter(({ s }) => {
        const isRunning = s.state === 'running';
        if (isRunning  && !showRunning) return false;
        if (!isRunning && !showStopped) return false;
        if (needle) {
            const name = (s.service ? s.service.replace(/\\.service$/, '') : s.container_name) || '';
            const ports = (s.ports || []).map(p => `${p.host_port} ${p.container_port}`).join(' ');
            const haystack = [name, s.image || '', s.quadlet_file || '', ports].join(' ').toLowerCase();
            if (!haystack.includes(needle)) return false;
        }
        return true;
    });

    const el = document.getElementById('services');
    if (!visible.length) {
        el.innerHTML = '<p class="text-gray-400 text-sm">Brak pasujących serwisów.</p>';
        return;
    }
    el.innerHTML = visible.map(({ s, i }) => _serviceCard(s, i)).join('');
}

async function loadServices() {
    const el = document.getElementById('services');
    try {
        _services = await fetch('/api/services').then(r => r.json());
        if (!_services.length) {
            el.innerHTML = '<p class="text-gray-400 text-sm">No containers or quadlet files found.</p>';
            return;
        }
        applyFilters();
    } catch(e) {
        el.innerHTML = `<p class="text-red-400 text-sm">Error: ${esc(String(e))}</p>`;
    }
}

function _showSvcOut(idx, text) {
    const wrap = document.getElementById(`svc-out-${idx}`);
    wrap.querySelector('pre').textContent = text;
    wrap.classList.remove('hidden');
}

function _toggleSvcOut(idx) {
    const wrap = document.getElementById(`svc-out-${idx}`);
    if (!wrap.classList.contains('hidden')) {
        wrap.classList.add('hidden');
        return true;
    }
    return false;
}

async function svcStatus(idx) {
    if (_toggleSvcOut(idx)) return;
    const s = _services[idx];
    _showSvcOut(idx, `Fetching status of ${s.service}…`);
    const d = await fetch(`/api/systemctl/${encodeURIComponent(s.service)}/status`).then(r => r.json());
    _showSvcOut(idx, d.output?.trim() || (d.ok ? 'active' : 'inactive'));
}

async function svcAction(idx, action) {
    const s = _services[idx];
    _showSvcOut(idx, `systemctl --user ${action} ${s.service}…`);
    const d = await fetch(`/api/systemctl/${encodeURIComponent(s.service)}/action`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action}),
    }).then(r => r.json());
    _showSvcOut(idx, d.output || (d.ok ? 'OK' : 'Failed'));
    toast(`${action} ${s.service}: ${d.ok ? 'OK' : 'failed'}`, d.ok);
    // Refresh after state-changing actions
    if (['start','stop','restart','enable','disable'].includes(action)) {
        setTimeout(loadServices, 800);
    }
}

async function podmanAction(idx, action) {
    const s = _services[idx];
    const id = s.container_id;
    _showSvcOut(idx, `podman ${action} ${s.container_name}…`);
    const d = await fetch(`/api/containers/${id}/action`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action}),
    }).then(r => r.json());
    _showSvcOut(idx, d.ok ? 'OK' : 'Failed');
    setTimeout(loadServices, 800);
}

async function pullImage(idx) {
    const s = _services[idx];
    _showSvcOut(idx, `podman pull ${s.image}…`);
    const d = await fetch(`/api/containers/${s.container_id}/update`, {method: 'POST'}).then(r => r.json());
    _showSvcOut(idx, d.ok ? 'Done' : 'Failed');
    setTimeout(loadServices, 800);
}

// ── Quadlet editor ────────────────────────────────────────────────────────────

let _editingQuadlet = '';
let _creatingNew = false;

function _openModal() {
    const modal = document.getElementById('edit-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function newQuadlet() {
    _creatingNew = true;
    _editingQuadlet = '';
    document.getElementById('modal-title').textContent = 'New Quadlet';
    document.getElementById('edit-filename').textContent = '';
    document.getElementById('edit-filename').classList.add('hidden');
    document.getElementById('new-filename-row').classList.remove('hidden');
    document.getElementById('new-filename').value = '';
    document.getElementById('quadlet-editor').value = `[Unit]
Description=

[Container]
Image=
ContainerName=

[Install]
WantedBy=default.target
`;
    _openModal();
    document.getElementById('new-filename').focus();
}

async function editSvc(idx) {
    _creatingNew = false;
    _editingQuadlet = _services[idx].quadlet_file;
    document.getElementById('modal-title').textContent = 'Edit Quadlet';
    document.getElementById('edit-filename').textContent = _editingQuadlet;
    document.getElementById('edit-filename').classList.remove('hidden');
    document.getElementById('new-filename-row').classList.add('hidden');
    const d = await fetch(`/api/quadlet/${encodeURIComponent(_editingQuadlet)}`).then(r => r.json());
    document.getElementById('quadlet-editor').value = d.content;
    _openModal();
}

function closeEditor() {
    document.getElementById('edit-modal').classList.replace('flex', 'hidden');
}

async function saveQuadlet() {
    const content = document.getElementById('quadlet-editor').value;

    if (_creatingNew) {
        let name = document.getElementById('new-filename').value.trim();
        if (!name) { toast('Filename is required', false); return; }
        if (!name.endsWith('.container')) name += '.container';
        const resp = await fetch('/api/quadlet', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, content}),
        });
        const d = await resp.json();
        if (!resp.ok) { toast(d.detail || 'Failed to create', false); return; }
        closeEditor();
        toast(d.reload_ok ? 'Created & daemon-reloaded ✓' : `Created — daemon-reload failed: ${d.reload_msg || '?'}`, d.reload_ok);
    } else {
        const d = await fetch(`/api/quadlet/${encodeURIComponent(_editingQuadlet)}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({content}),
        }).then(r => r.json());
        closeEditor();
        if (d.reload_ok) {
            toast('Saved & daemon-reloaded ✓');
        } else {
            toast(`Saved — daemon-reload failed: ${d.reload_msg || 'unknown error'}`, false);
        }
    }
    loadServices();
}

// ── Journal viewer ───────────────────────────────────────────────────────────

let _journalEvtSource = null;
let _journalService = '';

function openJournal(idx) {
    const s = _services[idx];
    _journalService = s.service;
    document.getElementById('journal-service').textContent = s.service;
    document.getElementById('journal-output').innerHTML = '<div class="text-gray-400" style="padding:2px 4px">Loading…</div>';
    document.getElementById('journal-follow').checked = true;
    const modal = document.getElementById('journal-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    startJournalStream();
}

function closeJournal() {
    stopJournalStream();
    document.getElementById('journal-modal').classList.replace('flex', 'hidden');
}

function stopJournalStream() {
    if (_journalEvtSource) {
        _journalEvtSource.close();
        _journalEvtSource = null;
    }
}

function _highlightLogLine(text) {
    // Highlight error/warning/critical keywords
    return text
        .replace(/\b(ERROR|error|Error|CRITICAL|critical|Critical|FATAL|fatal|Fatal)\b/g, '<span class="text-red-400 font-semibold">$1</span>')
        .replace(/\b(WARNING|warning|Warning|WARN|warn|Warn)\b/g, '<span class="text-yellow-400 font-semibold">$1</span>')
        .replace(/\b(INFO|info|Info)\b/g, '<span class="text-blue-300">$1</span>')
        .replace(/\b(DEBUG|debug|Debug)\b/g, '<span class="text-gray-500">$1</span>');
}

function startJournalStream() {
    stopJournalStream();
    const out = document.getElementById('journal-output');
    out.innerHTML = '';
    let lineNum = 0;
    _journalEvtSource = new EventSource(
        `/api/systemctl/${encodeURIComponent(_journalService)}/journal/stream?lines=200`
    );
    _journalEvtSource.onmessage = (e) => {
        const atBottom = out.scrollTop + out.clientHeight >= out.scrollHeight - 30;
        const line = document.createElement('div');
        line.className = lineNum % 2 === 0 ? 'bg-gray-700/40' : 'bg-gray-800/60';
        line.style.padding = '3px 6px';
        line.style.whiteSpace = 'pre-wrap';
        line.style.borderLeft = lineNum % 2 === 0 ? '2px solid #4b5563' : '2px solid transparent';
        line.innerHTML = _highlightLogLine(esc(e.data));
        out.appendChild(line);
        lineNum++;
        if (atBottom) out.scrollTop = out.scrollHeight;
    };
    _journalEvtSource.onerror = () => {
        const line = document.createElement('div');
        line.className = 'text-gray-500';
        line.style.padding = '3px 6px';
        line.textContent = '--- stream ended ---';
        out.appendChild(line);
        stopJournalStream();
    };
}

function toggleJournalFollow() {
    const follow = document.getElementById('journal-follow').checked;
    if (follow) {
        startJournalStream();
    } else {
        stopJournalStream();
    }
}

// ── Quick Commands ────────────────────────────────────────────────────────────

let _quickCommands = [];

async function loadQuickCommands() {
    const el = document.getElementById('quick-commands');
    const d = await fetch('/api/commands').then(r => r.json());
    _quickCommands = d.commands || [];
    if (!_quickCommands.length) {
        el.innerHTML = '<p class="text-gray-400 text-sm">No commands configured.<br>Add a <code class="text-gray-300">[commands]</code> section to <code class="text-gray-300">podmanpanel.toml</code>.</p>';
        return;
    }
    el.innerHTML = _quickCommands.map((c, i) => `
        <div class="flex items-center gap-2">
            <button id="qbtn-${i}" onclick="runQuickCommand(${i})"
                class="flex-1 text-left px-3 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm truncate"
                title="${esc(c.command)}">${esc(c.label)}</button>
            <span id="qstat-${i}" class="w-5 text-center shrink-0 text-base"></span>
        </div>
    `).join('');
}

async function runQuickCommand(idx) {
    const btn  = document.getElementById(`qbtn-${idx}`);
    const stat = document.getElementById(`qstat-${idx}`);
    const out  = document.getElementById('quick-output');
    btn.disabled = true;
    stat.textContent = '⏳';
    try {
        const d = await fetch('/api/commands', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({label: _quickCommands[idx].label}),
        }).then(r => r.json());
        stat.textContent = d.ok ? '✅' : '❌';
        const text = (d.stdout + d.stderr).trim();
        if (text) { out.textContent = text; out.classList.remove('hidden'); }
        setTimeout(() => { stat.textContent = ''; }, 5000);
    } catch(e) {
        stat.textContent = '❌';
    } finally {
        btn.disabled = false;
    }
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('edit-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeEditor();
    });
    document.getElementById('journal-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeJournal();
    });
});

loadInfo();
loadServices();
loadQuickCommands();
setInterval(loadServices, 30_000);
</script>
</body>
</html>"""


def setup_auth_interactive():
    """Prompt user to set up authentication if not configured."""
    import os
    import sys
    import secrets
    import bcrypt
    from pathlib import Path

    config_path = Path(os.getenv("PODMANPANEL_CONFIG", "podmanpanel.toml"))

    print("\n" + "=" * 60)
    print("  AUTHENTICATION NOT CONFIGURED")
    print("=" * 60)
    print("\nPodmanPanel will run WITHOUT authentication.")
    print("Anyone on your network will have full access.\n")

    setup = input("Set up authentication now? [Y/n]: ").strip().lower()
    if setup in ("", "y", "yes"):
        print()
        username = input("Enter username [admin]: ").strip() or "admin"
        password = input("Enter password: ").strip()

        if not password:
            print("Error: Password cannot be empty. Skipping auth setup.")
            print("Run 'python3 generate_auth.py' later to configure.\n")
            return

        print("\nGenerating secure configuration...")
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        secret_key = secrets.token_hex(32)

        # Append to config file
        auth_section = f"""
[auth]
username = "{username}"
password_hash = "{password_hash}"
secret_key = "{secret_key}"
"""
        if config_path.exists():
            content = config_path.read_text()
            if "[auth]" not in content:
                config_path.write_text(content.rstrip() + "\n" + auth_section)
        else:
            config_path.write_text(auth_section.lstrip())

        print(f"\n✓ Authentication configured in {config_path}")
        print("✓ Username:", username)
        print("\nPlease restart podmanpanel for changes to take effect.")
        sys.exit(0)
    else:
        print("\nSkipping authentication setup.")
        print("Run 'python3 generate_auth.py' later to configure.\n")


def main():
    import uvicorn
    import sys

    # Check if auth is configured; if not, prompt user
    if not AUTH_ENABLED and sys.stdin.isatty():
        setup_auth_interactive()

    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)


if __name__ == "__main__":
    main()
