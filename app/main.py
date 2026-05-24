import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from app.routers import containers, quadlet, commands
from app.routers import systemctl as systemctl_router
from app.routers import services as services_router
from app.config import STATIC_DIR, SERVER_HOST, SERVER_PORT, PODMAN_USER

app = FastAPI(title="PodmanPanel")

app.include_router(containers.router)
app.include_router(quadlet.router)
app.include_router(commands.router)
app.include_router(systemctl_router.router)
app.include_router(services_router.router)


@app.get("/api/info")
def info():
    return {"user": PODMAN_USER, "host": SERVER_HOST, "port": SERVER_PORT}


@app.get("/")
def index():
    path = Path(STATIC_DIR) / "index.html"
    if path.exists():
        return FileResponse(str(path))
    return HTMLResponse(INDEX_HTML)


@app.get("/static/{filename}")
def static_files(filename: str):
    return FileResponse(os.path.join(STATIC_DIR, filename))


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
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-semibold">Services</h2>
                    <button onclick="loadServices()" class="text-xs text-gray-400 hover:text-gray-200">&#x21bb; Refresh</button>
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

            <div class="bg-gray-800 rounded-lg p-4">
                <h2 class="text-xl font-semibold mb-4">Run Command</h2>
                <textarea id="cmd-input" rows="3"
                    class="w-full bg-gray-700 rounded p-2 text-sm font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"
                    placeholder="podman ps -a"></textarea>
                <button onclick="runCommand()"
                    class="mt-2 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded text-sm">Run</button>
                <pre id="cmd-output" class="mt-3 bg-gray-900 p-3 rounded text-xs overflow-auto max-h-64 hidden"></pre>
            </div>

        </div>
    </div>
</div>

<!-- Edit Modal -->
<div id="edit-modal" class="fixed inset-0 bg-black/80 hidden items-center justify-center z-50">
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4 flex flex-col" style="max-height:90vh">
        <h3 class="text-xl font-semibold mb-1">Edit Quadlet</h3>
        <p id="edit-filename" class="text-gray-400 text-sm mb-3"></p>
        <textarea id="quadlet-editor" rows="20"
            class="flex-1 bg-gray-900 p-3 rounded text-sm font-mono focus:outline-none focus:ring-1 focus:ring-blue-500 overflow-auto"></textarea>
        <div class="flex justify-end gap-2 mt-4">
            <button onclick="closeEditor()" class="px-4 py-2 rounded bg-gray-600 hover:bg-gray-700">Cancel</button>
            <button onclick="saveQuadlet()" class="px-4 py-2 rounded bg-green-600 hover:bg-green-700">Save + daemon-reload</button>
        </div>
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

async function loadServices() {
    const el = document.getElementById('services');
    try {
        _services = await fetch('/api/services').then(r => r.json());

        if (!_services.length) {
            el.innerHTML = '<p class="text-gray-400 text-sm">No containers or quadlet files found.</p>';
            return;
        }

        el.innerHTML = _services.map((s, i) => {
            const name = s.service ? s.service.replace(/\\.service$/, '') : s.container_name;
            const isManaged = !!s.service; // has a quadlet file

            const meta = [
                s.quadlet_file ? `<span class="text-gray-500 text-xs">${esc(s.quadlet_file)}</span>` : '',
                s.image        ? `<span class="text-gray-400 text-xs truncate">${esc(s.image)}</span>` : '',
            ].filter(Boolean).join(' ');

            // Action buttons for managed services (quadlet exists)
            const managedBtns = isManaged ? `
                <button onclick="editSvc(${i})"      class="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">Edit</button>
                <button onclick="svcStatus(${i})"    class="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">Status</button>
                <button onclick="svcAction(${i},'start')"   class="px-2 py-1 text-xs rounded bg-green-800 hover:bg-green-700">Start</button>
                <button onclick="svcAction(${i},'stop')"    class="px-2 py-1 text-xs rounded bg-red-800 hover:bg-red-700">Stop</button>
                <button onclick="svcAction(${i},'restart')" class="px-2 py-1 text-xs rounded bg-yellow-800 hover:bg-yellow-700">Restart</button>
                <button onclick="svcAction(${i},'enable')"  class="px-2 py-1 text-xs rounded bg-blue-900 hover:bg-blue-800">Enable</button>
                <button onclick="svcAction(${i},'disable')" class="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600">Disable</button>
            ` : '';

            // Podman action buttons (shown for containers, standalone or managed)
            const podmanBtns = s.container_id ? `
                <button onclick="podmanAction(${i},'${s.state === 'running' ? 'stop' : 'start'}')"
                    class="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600">
                    ${s.state === 'running' ? 'podman stop' : 'podman start'}
                </button>
                ${!isManaged ? `<button onclick="podmanAction(${i},'restart')" class="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600">Restart</button>
                <button onclick="pullImage(${i})" class="px-2 py-1 text-xs rounded bg-blue-900 hover:bg-blue-800">Pull</button>` : ''}
            ` : '';

            return `
            <div class="bg-gray-700 rounded p-3">
                <div class="flex flex-wrap items-center gap-x-2 gap-y-1 mb-2">
                    <span class="font-medium">${esc(name)}</span>
                    ${meta}
                    ${stateBadge(s.state)}
                    ${enabledBadge(s.enabled)}
                </div>
                <div class="flex flex-wrap gap-1">
                    ${managedBtns}
                    ${podmanBtns}
                </div>
                <div id="svc-out-${i}" class="hidden mt-2">
                    <pre class="bg-gray-900 p-2 rounded text-xs overflow-auto max-h-48 whitespace-pre-wrap"></pre>
                </div>
            </div>`;
        }).join('');

    } catch(e) {
        el.innerHTML = `<p class="text-red-400 text-sm">Error: ${esc(String(e))}</p>`;
    }
}

function _showSvcOut(idx, text) {
    const wrap = document.getElementById(`svc-out-${idx}`);
    wrap.querySelector('pre').textContent = text;
    wrap.classList.remove('hidden');
}

async function svcStatus(idx) {
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

async function editSvc(idx) {
    _editingQuadlet = _services[idx].quadlet_file;
    document.getElementById('edit-filename').textContent = _editingQuadlet;
    const d = await fetch(`/api/quadlet/${encodeURIComponent(_editingQuadlet)}`).then(r => r.json());
    document.getElementById('quadlet-editor').value = d.content;
    const modal = document.getElementById('edit-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeEditor() {
    document.getElementById('edit-modal').classList.replace('flex', 'hidden');
}

async function saveQuadlet() {
    const content = document.getElementById('quadlet-editor').value;
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
    loadServices();
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
            body: JSON.stringify({command: _quickCommands[idx].command}),
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

// ── Run Command ───────────────────────────────────────────────────────────────

async function runCommand() {
    const cmd = document.getElementById('cmd-input').value.trim();
    if (!cmd) return;
    const out = document.getElementById('cmd-output');
    out.textContent = 'Running…';
    out.classList.remove('hidden');
    const d = await fetch('/api/commands', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({command: cmd}),
    }).then(r => r.json());
    out.textContent = (d.ok ? '✓ ' : '✗ ') + (d.stdout + d.stderr).trim();
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('cmd-input').addEventListener('keydown', e => {
        if (e.ctrlKey && e.key === 'Enter') runCommand();
    });
    document.getElementById('edit-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeEditor();
    });
});

loadInfo();
loadServices();
loadQuickCommands();
setInterval(loadServices, 30_000);
</script>
</body>
</html>"""


def main():
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)


if __name__ == "__main__":
    main()
