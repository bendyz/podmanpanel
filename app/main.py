import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from app.routers import containers, quadlet, commands
from app.config import PODMAN_USER, STATIC_DIR

app = FastAPI(title="PodmanPanel")

app.include_router(containers.router)
app.include_router(quadlet.router)
app.include_router(commands.router)


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
        <h1 class="text-3xl font-bold mb-6">PodmanPanel <span class="text-sm text-gray-400">user: """ + PODMAN_USER + """</span></h1>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2">
                <div class="bg-gray-800 rounded-lg p-4">
                    <h2 class="text-xl font-semibold mb-4">Containers</h2>
                    <div id="containers" class="space-y-2"></div>
                </div>

                <div class="bg-gray-800 rounded-lg p-4 mt-6">
                    <h2 class="text-xl font-semibold mb-4">Quadlet Files</h2>
                    <div id="quadlet-list" class="space-y-2"></div>
                </div>
            </div>

            <div class="bg-gray-800 rounded-lg p-4 h-fit">
                <h2 class="text-xl font-semibold mb-4">Run Command</h2>
                <textarea id="cmd-input" rows="3" class="w-full bg-gray-700 rounded p-2 text-sm" placeholder="podman ps -a"></textarea>
                <button onclick="runCommand()" class="mt-2 bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded">Run</button>
                <pre id="cmd-output" class="mt-4 bg-gray-900 p-3 rounded text-xs overflow-auto max-h-64"></pre>
            </div>
        </div>
    </div>

    <div id="edit-modal" class="fixed inset-0 bg-black/80 hidden items-center justify-center">
        <div class="bg-gray-800 rounded-lg p-6 w-full max-w-2xl">
            <h3 class="text-xl font-semibold mb-4">Edit Quadlet</h3>
            <textarea id="quadlet-editor" rows="20" class="w-full bg-gray-900 p-3 rounded text-sm font-mono"></textarea>
            <div class="flex justify-end gap-2 mt-4">
                <button onclick="closeEditor()" class="px-4 py-2 rounded bg-gray-600 hover:bg-gray-700">Cancel</button>
                <button onclick="saveQuadlet()" class="px-4 py-2 rounded bg-green-600 hover:bg-green-700">Save</button>
            </div>
        </div>
    </div>

    <script>
        async function loadContainers() {
            const res = await fetch('/api/containers');
            const data = await res.json();
            const container = document.getElementById('containers');
            if (!data.length) {
                container.innerHTML = '<p class="text-gray-400">No containers found</p>';
                return;
            }
            container.innerHTML = data.map(c => `
                <div class="bg-gray-700 rounded p-3 flex items-center justify-between">
                    <div>
                        <span class="font-medium">${c.Names || c.Id?.slice(0,12)}</span>
                        <span class="text-gray-400 text-sm ml-2">${c.Image}</span>
                        <span class="text-xs ml-2 px-2 py-0.5 rounded ${c.State === 'running' ? 'bg-green-600' : 'bg-gray-600'}">${c.State}</span>
                    </div>
                    <div class="flex gap-1">
                        <button onclick="doAction('${c.Id}', '${c.State === 'running' ? 'stop' : 'start'}')" class="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">${c.State === 'running' ? 'Stop' : 'Start'}</button>
                        <button onclick="doAction('${c.Id}', 'restart')" class="px-2 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">Restart</button>
                        <button onclick="updateImage('${c.Id}')" class="px-2 py-1 text-xs rounded bg-blue-600 hover:bg-blue-500">Pull</button>
                    </div>
                </div>
            `).join('');
        }

        async function doAction(id, action) {
            await fetch(`/api/containers/${id}/action`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action})
            });
            loadContainers();
        }

        async function updateImage(id) {
            await fetch(`/api/containers/${id}/update`, {method: 'POST'});
            loadContainers();
        }

        async function loadQuadlet() {
            const res = await fetch('/api/quadlet');
            const data = await res.json();
            const container = document.getElementById('quadlet-list');
            if (!data.files?.length) {
                container.innerHTML = '<p class="text-gray-400">No quadlet files found</p>';
                return;
            }
            container.innerHTML = data.files.map(f => `
                <div class="bg-gray-700 rounded p-3 flex items-center justify-between">
                    <span class="font-medium">${f}</span>
                    <button onclick="editQuadlet('${f}')" class="px-3 py-1 text-xs rounded bg-gray-600 hover:bg-gray-500">Edit</button>
                </div>
            `).join('');
        }

        let currentQuadlet = '';
        async function editQuadlet(name) {
            currentQuadlet = name;
            const res = await fetch(`/api/quadlet/${name}`);
            const data = await res.json();
            document.getElementById('quadlet-editor').value = data.content;
            document.getElementById('edit-modal').classList.remove('hidden');
            document.getElementById('edit-modal').classList.add('flex');
        }

        function closeEditor() {
            document.getElementById('edit-modal').classList.add('hidden');
            document.getElementById('edit-modal').classList.remove('flex');
        }

        async function saveQuadlet() {
            const content = document.getElementById('quadlet-editor').value;
            await fetch(`/api/quadlet/${currentQuadlet}`, {
                method: 'PUT',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content})
            });
            closeEditor();
            loadQuadlet();
        }

        async function runCommand() {
            const cmd = document.getElementById('cmd-input').value;
            const output = document.getElementById('cmd-output');
            output.textContent = 'Running...';
            const res = await fetch('/api/commands', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmd})
            });
            const data = await res.json();
            output.textContent = (data.ok ? '✓ ' : '✗ ') + (data.stdout || data.stderr || '');
        }

        loadContainers();
        loadQuadlet();
    </script>
</body>
</html>"""


def main():
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)


if __name__ == "__main__":
    main()