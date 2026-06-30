#!/usr/bin/env python3
"""
FastAPI dashboard for ARKA bot.
Provides a simple web UI to manage VRChat cookie, view instances, and system stats.
"""
import os
from typing import Any, Dict

import psutil
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

def get_bot(request: Request) -> Any:
    bot: Any = getattr(request.app.state, "bot", None)
    if bot is None:
        raise RuntimeError("Bot instance not attached to app")
    return bot

def create_app(bot: Any) -> FastAPI:
    app = FastAPI(title="ARKA Dashboard")
    app.state.bot = bot

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    template_dir = os.path.join(BASE_DIR, "templates")
    static_dir = os.path.join(BASE_DIR, "static")
    templates = Jinja2Templates(directory=template_dir) if os.path.isdir(template_dir) else None
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Helper to get VRChat cog
    def get_vrchat_cog():
        cog = bot.get_cog("VRChatCog")
        if cog is None:
            raise RuntimeError("VRChatCog not loaded")
        return cog

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        # Simple inline HTML to avoid template dependency
        html_content = """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>ARKA Dashboard</title>
            <style>
                body {font-family: Arial, sans-serif; margin:0; padding:0; background:#f4f4f4;}
                header {background:#2c3e50; color:#fff; padding:1rem; text-align:center;}
                nav {display:flex; justify-content:center; background:#34495e;}
                nav a {color:#ecf0f1; padding:0.8rem 1.5rem; text-decoration:none;}
                nav a:hover, .active {background:#1abc9c;}
                .container {display:flex; margin:2rem;}
                sidebar {width:250px; background:#ecf0f1; padding:1rem;}
                main {flex:1; padding:1rem;}
                .card {background:#fff; margin-bottom:1.5rem; padding:1rem; border-radius:5px; box-shadow:0 2px 5px rgba(0,0,0,0.1);}
                h2 {margin-top:0;}
                pre {background:#f8f8f8; padding:1rem; overflow:auto;}
                input[type=password] {width:100%; padding:0.5rem;}
                button {margin-top:0.5rem; padding:0.5rem 1rem; background:#1abc9c; color:#fff; border:none; cursor:pointer;}
                button:hover {background:#16a085;}
                .status {font-weight:bold;}
                .status.ok {color:#2ecc71;}
                .status.error {color:#e74c3c;}
            </style>
        </head>
        <body>
            <header><h1>ARKA Dashboard</h1></header>
            <nav>
                <a href="#auth" onclick="showTab('auth')">VRChat Auth</a>
                <a href="#instances" onclick="showTab('instances')">VRChat Instances</a>
                <a href="#system" onclick="showTab('system')">Système RPi4</a>
            </nav>
            <div class="container">
                <sidebar>
                    <h3>Navigation</h3>
                </sidebar>
                <main>
                    <section id="auth" class="tab active">
                        <div class="card">
                            <h2>Authentification VRChat</h2>
                            <p>Entrez votre cookie d'authentification (auth) pour maintenir la connexion au compte bot.</p>
                            <input type="password" id="vrchatCookie" placeholder="Cookie auth">
                            <button onclick="setCookie()">Enregistrer</button>
                            <div id="cookieStatus" class="status"></div>
                        </div>
                    </section>
                    <section id="instances" class="tab">
                        <div class="card">
                            <h2>Instances VRChat du groupe Arkana</h2>
                            <div id="instancesList">Chargement…</div>
                        </div>
                    </section>
                    <section id="system" class="tab">
                        <div class="card">
                            <h2>Statut du Raspberry Pi</h2>
                            <div id="sysInfo">Chargement…</div>
                        </div>
                    </section>
                </main>
            </div>
            <script>
                function showTab(tabName) {
                    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                    document.querySelectorAll('nav a').forEach(a => a.classList.remove('active'));
                    document.getElementById(tabName).classList.add('active');
                    event.target.classList.add('active');
                }
                async function setCookie() {
                    const cookie = document.getElementById('vrchatCookie').value.trim();
                    const resp = await fetch('/api/vrchat/setcookie', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({cookie: cookie})
                    });
                    const data = await resp.json();
                    document.getElementById('cookieStatus').textContent = data.message;
                    document.getElementById('cookieStatus').className = 'status ' + (data.ok ? 'ok' : 'error');
                }
                async function loadInstances() {
                    const resp = await fetch('/api/vrchat/instances');
                    const data = await resp.json();
                    const container = document.getElementById('instancesList');
                    if (data.length === 0) {
                        container.innerHTML = '<i>Aucune instance trouvée ou cookie non défini.</i>';
                        return;
                    }
                    let html = '<ul>';
                    for (const i of data) {
                        html += `<li><strong>${i.name||'Inconnu'}</strong> (${i.nUsers}/${i.capacity||'?'}) - <code>${i.id}</code></li>`;
                    }
                    html += '</ul>';
                    container.innerHTML = html;
                }
                async function loadSystem() {
                    const resp = await fetch('/api/system/stats');
                    const data = await resp.json();
                    const container = document.getElementById('sysInfo');
                    let html = `<p><strong>CPU:</strong> ${data.cpu_percent}%</p>`;
                    html += `<p><strong>RAM:</strong> ${Math.round(data.memory_used / 1024 / 1024)} MB / ${Math.round(data.memory_total / 1024 / 1024)} MB (${data.memory_percent}%)</p>`;
                    if (data.temperature !== null) {
                        html += `<p><strong>Température:</strong> ${data.temperature}°C</p>`;
                    } else {
                        html += `<p><strong>Température:</strong> non disponible</p>`;
                    }
                    container.innerHTML = html;
                }
                // Auto-refresh data every 15 seconds
                setInterval(loadInstances, 15000);
                setInterval(loadSystem, 15000);
                // Initial load
                loadInstances();
                loadSystem();
            </script>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)

    @app.post("/api/vrchat/setcookie")
    async def set_vrchat_cookie(payload: dict, bot: Any = Depends(get_bot)):
        cookie = payload.get("cookie", "").strip()
        if not cookie:
            raise HTTPException(status_code=400, detail="Cookie missing")
        cog = get_vrchat_cog()
        cog.set_cookie(cookie)
        return JSONResponse({"ok": True, "message": "Cookie enregistré."})

    @app.get("/api/vrchat/instances")
    async def get_vrchat_instances(bot: Any = Depends(get_bot)):
        cog = get_vrchat_cog()
        data = cog.get_current_instances()
        result = []
        for iid, info in data.items():
            result.append({
                "id": iid,
                "name": info.get("name", "Inconnu"),
                "nUsers": info.get("nUsers", 0),
                "capacity": info.get("capacity", 0),
            })
        return JSONResponse(result)

    @app.get("/api/system/stats")
    async def get_system_stats():
        cpu = psutil.cpu_percent(interval=0.5)
        mem = psutil.virtual_memory()
        temp = None
        try:
            temps = psutil.sensors_temperatures()
            if 'cpu_thermal' in temps:
                temp = temps['cpu_thermal'][0].current
            elif 'cpu-thermal' in temps:
                temp = temps['cpu-thermal'][0].current
            elif 'coretemp' in temps:
                temps_list = [t.current for t in temps['coretemp'] if t.current is not None]
                if temps_list:
                    temp = sum(temps_list) / len(temps_list)
        except Exception:
            temp = None
        return JSONResponse({
            "cpu_percent": cpu,
            "memory_used": mem.used,
            "memory_total": mem.total,
            "memory_percent": mem.percent,
            "temperature": temp,
        })

    @app.get("/api/logs")
    async def get_logs(lines: int = 100):
        log_path = os.path.join(os.path.dirname(__file__), "..", "arka.log")
        if not os.path.exists(log_path):
            return PlainTextResponse("Log file not found.", status_code=404)
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                last = "".join(all_lines[-lines:])
            return PlainTextResponse(last)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return app