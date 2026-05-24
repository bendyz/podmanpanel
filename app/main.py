import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from app.routers import containers, quadlet, commands
from app.routers import systemctl as systemctl_router
from app.config import STATIC_DIR, SERVER_HOST, SERVER_PORT, PODMAN_USER

app = FastAPI(title="PodmanPanel")

app.include_router(containers.router)
app.include_router(quadlet.router)
app.include_router(commands.router)
app.include_router(systemctl_router.router)


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

        <!-- Left column -->
        <div class="lg:col-span-2 space-y-6">

            <!-- Containers -->
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-semibold">Containers</h2>
                    <button onclick="loadContainers()" class="text-xs text-gray-400 hover:text-gray-200">&#x21bb; Refresh</button>
                </div>
                <div id="containers" class="space-y-2">
                    <p class="text-gray-400 text-sm">Loading...</p>
                </div>
            </div>

            <!-- Quadlet Files -->
            <div class="bg-gray-800 rounded-lg p-4">
                <div class="flex items-center justify-between mb-4">
                    <h2 class="text-xl font-semibold">Quadlet Files</h2>
                    <button onclick="loadQuadlet()" class="text-xs text-gray-400 hover:text-gray-200">&#x21bb; Refresh</button>
                </div>
                <div id="quadlet-list" class="space-y-2">
                    <p class="text-gray-400 text-sm">Loading...</p>
                </div>
            </div>

        </div>

        <!-- Right column -->
        <div class="space-y-6">

            <!-- Quick Commands -->
            <div class="bg-gray-800 rounded-lg p-4">
                <h2 class="text-xl font-semibold mb-4">Quick Commands</h2>
                <div id="quick-commands" class="space-y-2">
                    <p class="text-gray-400 text-sm">Loading...</p>
                </div>
                <pre id="quick-output" class="mt-3 bg-gray-900 p-3 rounded text-xs overflow-auto max-h-48 hidden"></pre>
            </div>

            <!-- Run Command -->
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
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-2xl mx-4">
        <h3 class="text-xl font-semibold mb-4">Edit Quadlet: <span id="edit-filename" class="text-gray-400 font-normal text-base"></span></h3>
        <textarea id="quadlet-editor" rows="20"
            class="w-full bg-gray-900 p-3 rounded text-sm font-mono focus:outline-none focus:ring-1 focus:ring-blue-500"></textarea>
        <div class="flex justify-end gap-2 mt-4">
            <button onclick="closeEditor()" class="px-4 py-2 rounded bg-gray-600 hover:bg-gray-700">Cancel</button>
            <button onclick="saveQuadlet()" class="px-4 py-2 rounded bg-green-600 hover:bg-green-700">Save</button>
        </div>
    </div>
</div>

<script>
// ── Helpers ──────────────────────────────────────────────────────────────────

function esc(s) {
    return String(s ?? '')
        .replace(/&/g,'&amp;').replace(/</g,'&lt;')
        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function stateBadge(state) {
    const running = state === 'running';
    const paused  = state === 'paused';
    const color   = running ? 'bg-green-700' : paused ? 'bg-yellow-700' : 'bg-gray-600';
    return `<span class="text-xs px-2 py-0.5 rounded ${color}">${esc(state)}</span>`;
}

// ── Info ─────────────────────────────────────────────────────────────────────

async function loadInfo() {
    try {
        const d = await fetch('/api/info').then(r => r.json());
        document.getElementById('podman-user').textContent = 'user: ' + d.user;
    } catch(e) {}
}

// ── Containers ────────────────────────────────────────────────────────────────

let _containers = [];

async function loadContainers() {
    const el = document.getElementById('containers');
    try {
        _containers = await fetch('/api/containers').then(r => r.json());
        if (!_containers.length) {
            el.innerHTML = '<p class="text-gray-400 text-sm">No containers found</p>';
            return;
        }
        el.innerHTML = _containers.map((c, i) => {
            const running = c.State === 'running';
            const toggleLabel = running ? 'Stop' : 'Start';
            const toggleAction = running ? 'stop' : 'start';
            return `
            <div class="bg-gray-700 rounded p-3 flex flex-wrap items-center gap-2">
                <div class="flex-1 min-w-0">
                    <span class="font-medium">${esc(c.Names || c.Id.slice(0,12))}</span>
                    <span class="text-gray-400 text-xs ml-2 truncate">${esc(c.Image)}</span>
                    ${stateBadge(c.State)}
                </div>
                <div class="flex gap-1 shrink-0">
                    <button onclick="containerAction(${i},'${toggleAction}')"
                        class="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">${toggleLabel}</button>
                    <button onclick="containerAction(${i},'restart')"
                        class="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">Restart</button>
                    <button onclick="pullImage(${i})"
                        class="px-2 py-1 text-xs rounded bg-blue-700 hover:bg-blue-600">Pull</button>
                </div>
            </div>`;
        }).join('');
    } catch(e) {
        el.innerHTML = `<p class="text-red-400 text-sm">Error: ${esc(String(e))}</p>`;
    }
}

async function containerAction(idx, action) {
    const id = _containers[idx].Id;
    await fetch(`/api/containers/${id}/action`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({action}),
    });
    loadContainers();
}

async function pullImage(idx) {
    const id = _containers[idx].Id;
    await fetch(`/api/containers/${id}/update`, {method: 'POST'});
    loadContainers();
}

// ── Quadlet Files ─────────────────────────────────────────────────────────────

let _quadlets = [];

async function loadQuadlet() {
    const el = document.getElementById('quadlet-list');
    try {
        const data = await fetch('/api/quadlet').then(r => r.json());
        _quadlets = data.files || [];
        if (!_quadlets.length) {
            el.innerHTML = '<p class="text-gray-400 text-sm">No .container files found in ~/.config/containers/systemd/</p>';
            return;
        }
        el.innerHTML = _quadlets.map((f, i) => `
            <div class="bg-gray-700 rounded p-3">
                <div class="flex flex-wrap items-center gap-2">
                    <span class="font-medium text-sm flex-1">${esc(f.name)}</span>
                    <div class="flex flex-wrap gap-1">
                        <button onclick="editQuadlet(${i})"
                            class="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">Edit</button>
                        <button onclick="sysctl(${i},'status')"
                            class="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">Status</button>
                        <button onclick="sysctl(${i},'start')"
                            class="px-2 py-1 text-xs rounded bg-green-800 hover:bg-green-700">Start</button>
                        <button onclick="sysctl(${i},'stop')"
                            class="px-2 py-1 text-xs rounded bg-red-800 hover:bg-red-700">Stop</button>
                        <button onclick="sysctl(${i},'restart')"
                            class="px-2 py-1 text-xs rounded bg-yellow-800 hover:bg-yellow-700">Restart</button>
                    </div>
                </div>
                <div id="sysctl-out-${i}" class="hidden mt-2">
                    <pre class="bg-gray-900 p-2 rounded text-xs overflow-auto max-h-48 whitespace-pre-wrap"></pre>
                </div>
            </div>
        `).join('');
    } catch(e) {
        el.innerHTML = `<p class="text-red-400 text-sm">Error: ${esc(String(e))}</p>`;
    }
}

async function sysctl(idx, action) {
    const f = _quadlets[idx];
    const outWrap = document.getElementById(`sysctl-out-${idx}`);
    const pre = outWrap.querySelector('pre');
    outWrap.classList.remove('hidden');
    pre.textContent = `systemctl --user ${action} ${f.service}…`;

    let res;
    if (action === 'status') {
        res = await fetch(`/api/systemctl/${encodeURIComponent(f.service)}/status`).then(r => r.json());
    } else {
        res = await fetch(`/api/systemctl/${encodeURIComponent(f.service)}/action`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({action}),
        }).then(r => r.json());
        loadContainers();
    }
    pre.textContent = res.output?.trim() || (res.ok ? 'OK' : 'Failed (no output)');
}

// ── Quadlet editor ───────────────────────────────────────────────────────────

let _editingQuadlet = '';

async function editQuadlet(idx) {
    _editingQuadlet = _quadlets[idx].name;
    document.getElementById('edit-filename').textContent = _editingQuadlet;
    const data = await fetch(`/api/quadlet/${encodeURIComponent(_editingQuadlet)}`).then(r => r.json());
    document.getElementById('quadlet-editor').value = data.content;
    const modal = document.getElementById('edit-modal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeEditor() {
    const modal = document.getElementById('edit-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

async function saveQuadlet() {
    const content = document.getElementById('quadlet-editor').value;
    await fetch(`/api/quadlet/${encodeURIComponent(_editingQuadlet)}`, {
        method: 'PUT',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({content}),
    });
    closeEditor();
    loadQuadlet();
}

// ── Quick Commands ────────────────────────────────────────────────────────────

let _quickCommands = [];

async function loadQuickCommands() {
    const el = document.getElementById('quick-commands');
    const data = await fetch('/api/commands').then(r => r.json());
    _quickCommands = data.commands || [];

    if (!_quickCommands.length) {
        el.innerHTML = '<p class="text-gray-400 text-sm">No commands configured.<br>Add a <code class="text-gray-300">[commands]</code> section to <code class="text-gray-300">podmanpanel.toml</code>.</p>';
        return;
    }

    el.innerHTML = _quickCommands.map((c, i) => `
        <div class="flex items-center gap-2">
            <button id="qbtn-${i}" onclick="runQuickCommand(${i})"
                class="flex-1 text-left px-3 py-2 rounded bg-gray-700 hover:bg-gray-600 text-sm truncate"
                title="${esc(c.command)}">${esc(c.label)}</button>
            <span id="qstat-${i}" class="text-base w-5 text-center shrink-0"></span>
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
        const data = await fetch('/api/commands', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({command: _quickCommands[idx].command}),
        }).then(r => r.json());

        stat.textContent = data.ok ? '✅' : '❌';
        const text = (data.stdout + data.stderr).trim();
        if (text) {
            out.textContent = text;
            out.classList.remove('hidden');
        }
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
    const data = await fetch('/api/commands', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({command: cmd}),
    }).then(r => r.json());
    out.textContent = (data.ok ? '✓ ' : '✗ ') + (data.stdout + data.stderr).trim();
}

// Allow Ctrl+Enter to submit the command box
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('cmd-input').addEventListener('keydown', e => {
        if (e.ctrlKey && e.key === 'Enter') runCommand();
    });
    // Close modal on backdrop click
    document.getElementById('edit-modal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeEditor();
    });
});

// ── Init ──────────────────────────────────────────────────────────────────────

loadInfo();
loadContainers();
loadQuadlet();
loadQuickCommands();

// Auto-refresh container states every 30 s
setInterval(loadContainers, 30_000);
</script>
</body>
</html>"""


def main():
    import uvicorn
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)


if __name__ == "__main__":
    main()
