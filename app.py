import os
import json
import base64
import urllib.request
import urllib.error
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 8080))
ADMIN_USER = os.environ.get("ADMIN_USER", "xfreexareana.ai")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "xfreexareana.ai@778605")
API_KEY = os.environ.get("API_KEY", "sk-zai-termux-free")

VALID_KEYS = {API_KEY, "sk-zai-termux-free"}
UPSTREAM_URL = "https://text.pollinations.ai/openai/chat/completions"

STATS = {
    "start_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    "total_requests": 0,
    "total_tokens": 0,
    "recent_logs": []
}

ZAI_MODELS = [
    {"id": "glm-5.3-flash", "object": "model", "owned_by": "z.ai"},
    {"id": "glm-5.2", "object": "model", "owned_by": "z.ai"},
    {"id": "glm-5", "object": "model", "owned_by": "z.ai"},
    {"id": "glm-4.7", "object": "model", "owned_by": "z.ai"},
    {"id": "glm-4.6", "object": "model", "owned_by": "z.ai"},
    {"id": "glm-4.6-air", "object": "model", "owned_by": "z.ai"},
    {"id": "glm-4.5", "object": "model", "owned_by": "z.ai"},
    {"id": "glm-4-flash", "object": "model", "owned_by": "z.ai"},
    {"id": "chatglm-3", "object": "model", "owned_by": "z.ai"}
]

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Z.ai Dedicated Proxy Dashboard</title>
<style>
  :root {
    --bg: #090d16; --card: #131b2e; --border: #1f2d4d; --text: #f1f5f9;
    --muted: #8e9bb5; --primary: #38bdf8; --success: #34d399; --danger: #f87171;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  body { background: var(--bg); color: var(--text); min-height: 100vh; display: flex; flex-direction: column; }
  #login-view { display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }
  .login-card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 32px; width: 100%; max-width: 400px; }
  .login-title { font-size: 1.5rem; font-weight: 700; color: var(--primary); text-align: center; margin-bottom: 6px; }
  .login-sub { font-size: 0.85rem; color: var(--muted); text-align: center; margin-bottom: 24px; }
  .form-group { margin-bottom: 18px; }
  .form-label { display: block; font-size: 0.85rem; color: var(--muted); margin-bottom: 6px; }
  .form-input { width: 100%; background: #090d16; border: 1px solid var(--border); border-radius: 8px; padding: 12px; color: #fff; font-size: 0.95rem; outline: none; }
  .btn-submit { width: 100%; background: var(--primary); color: #000; border: none; padding: 12px; border-radius: 8px; font-weight: 700; cursor: pointer; }
  .login-err { color: var(--danger); font-size: 0.85rem; text-align: center; margin-top: 14px; display: none; }

  #dash-view { display: none; padding: 24px; }
  .container { max-width: 1000px; margin: 0 auto; width: 100%; }
  .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 18px; margin-bottom: 24px; }
  .badge { background: #1f2d4d; padding: 6px 12px; border-radius: 999px; font-size: 0.85rem; }
  .btn-logout { background: transparent; border: 1px solid var(--danger); color: var(--danger); padding: 6px 14px; border-radius: 6px; cursor: pointer; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
  .stat-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; }
  .stat-label { color: var(--muted); font-size: 0.8rem; font-weight: 600; text-transform: uppercase; }
  .stat-num { font-size: 2rem; font-weight: 800; margin-top: 8px; }
  .table-card { background: var(--card); border: 1px solid var(--border); border-radius: 12px; padding: 20px; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left; }
  th { color: var(--muted); padding: 12px; border-bottom: 1px solid var(--border); }
  td { padding: 12px; border-bottom: 1px solid #1a253c; }
</style>
<script>
  let token = localStorage.getItem('zai_dash_auth');
  async function tryLogin() {
    const u = document.getElementById('login-u').value.trim();
    const p = document.getElementById('login-p').value.trim();
    const cred = btoa(u + ':' + p);
    const res = await fetch('/api/stats', { headers: { 'Authorization': 'Basic ' + cred } });
    if (res.status === 200) {
      token = cred;
      localStorage.setItem('zai_dash_auth', cred);
      showDashboard();
    } else {
      document.getElementById('login-err').style.display = 'block';
    }
  }
  function logout() { localStorage.removeItem('zai_dash_auth'); location.reload(); }
  function showDashboard() {
    document.getElementById('login-view').style.display = 'none';
    document.getElementById('dash-view').style.display = 'block';
    loadStats(); setInterval(loadStats, 3000);
  }
  async function loadStats() {
    if (!token) return;
    try {
      const res = await fetch('/api/stats', { headers: { 'Authorization': 'Basic ' + token } });
      if (res.status !== 200) { logout(); return; }
      const d = await res.json();
      document.getElementById('total-req').innerText = d.total_requests;
      document.getElementById('total-tok').innerText = d.total_tokens.toLocaleString();
      const tbody = document.getElementById('log-rows');
      tbody.innerHTML = '';
      if (!d.recent_logs || d.recent_logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--muted)">No requests yet</td></tr>';
        return;
      }
      d.recent_logs.forEach(l => {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${l.time}</td><td>${l.type}</td><td>${l.model}</td><td style="color:var(--success)">${l.status}</td>`;
        tbody.appendChild(tr);
      });
    } catch(e) {}
  }
  window.addEventListener('DOMContentLoaded', () => { if (token) showDashboard(); });
</script>
</head>
<body>
  <div id="login-view">
    <div class="login-card">
      <div class="login-title">⚡ Z.ai2api Dedicated</div>
      <div class="login-sub">Sign in to Z.ai Dashboard</div>
      <div class="form-group">
        <label class="form-label">Username</label>
        <input class="form-input" id="login-u" type="text" placeholder="xfreexareana.ai">
      </div>
      <div class="form-group">
        <label class="form-label">Password</label>
        <input class="form-input" id="login-p" type="password" placeholder="••••••••">
      </div>
      <button class="btn-submit" onclick="tryLogin()">Log In</button>
      <div class="login-err" id="login-err">Invalid username or password</div>
    </div>
  </div>

  <div id="dash-view">
    <div class="container">
      <div class="header">
        <div>
          <div style="font-size: 1.4rem; font-weight: 800; color: var(--primary);">⚡ Z.ai Dedicated Proxy</div>
          <div style="color: var(--muted); font-size: 0.85rem; margin-top: 4px;">GLM-5.3-Flash / GLM-4.6 / ChatGLM API</div>
        </div>
        <div style="display: flex; align-items: center; gap: 10px;">
          <div class="badge">👤 xfreexareana.ai</div>
          <button class="btn-logout" onclick="logout()">Log Out</button>
        </div>
      </div>
      <div class="grid">
        <div class="stat-card">
          <div class="stat-label">Total Z.ai Calls</div>
          <div class="stat-num" style="color:var(--primary)" id="total-req">0</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Total Tokens</div>
          <div class="stat-num" style="color:var(--success)" id="total-tok">0</div>
        </div>
      </div>
      <div class="table-card">
        <h3 style="margin-bottom: 16px;">Live Activity Logs</h3>
        <table>
          <thead><tr><th>Time</th><th>Endpoint</th><th>Model</th><th>Status</th></tr></thead>
          <tbody id="log-rows"><tr><td colspan="4" style="text-align:center;color:var(--muted)">Loading...</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>
</body>
</html>
"""

class ZaiProxyHandler(BaseHTTPRequestHandler):
    def _send_json(self, status_code, data):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-api-key, anthropic-version")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, x-api-key, anthropic-version")
        self.end_headers()

    def _check_admin(self):
        auth_header = self.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Basic "):
            return False
        try:
            user, pwd = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8").split(":", 1)
            return user == ADMIN_USER and pwd == ADMIN_PASS
        except Exception:
            return False

    def _verify_api(self):
        auth_header = self.headers.get("Authorization", "") or self.headers.get("x-api-key", "")
        if not auth_header:
            return True
        token = auth_header.replace("Bearer ", "").strip()
        return (token in VALID_KEYS) or token.startswith("sk-")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/dashboard", "/dashboard/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))
            return
        if path == "/api/stats":
            if not self._check_admin():
                self._send_json(401, {"error": "Unauthorized"})
                return
            self._send_json(200, STATS)
            return
        if path == "/":
            self._send_json(200, {"status": "online", "name": "Z.ai2api Dedicated", "dashboard": "/dashboard"})
            return
        if path in ("/v1/models", "/models"):
            self._send_json(200, {"object": "list", "data": ZAI_MODELS})
            return
        self._send_json(404, {"error": {"message": f"Endpoint not found: {path}"}})

    def do_POST(self):
        path = self.path.split("?")[0]
        if not self._verify_api():
            self._send_json(401, {"error": {"message": "Invalid API key"}})
            return

        content_len = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_len)
        try:
            body = json.loads(post_data.decode("utf-8"))
        except Exception:
            self._send_json(400, {"error": {"message": "Invalid JSON"}})
            return

        req_model = body.get("model", "glm-5.3-flash")

        # Handle Anthropic /v1/messages
        if path in ("/v1/messages", "/messages"):
            anthropic_messages = body.get("messages", [])
            openai_messages = []
            for m in anthropic_messages:
                content = m.get("content", "")
                if isinstance(content, list):
                    content = "\n".join([p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"])
                openai_messages.append({"role": m.get("role", "user"), "content": content})

            payload = {"model": "openai-fast", "messages": openai_messages}
            req = urllib.request.Request(
                UPSTREAM_URL,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "zai2api-render"}
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as res:
                    upstream = json.loads(res.read().decode("utf-8"))
                    text_out = upstream["choices"][0]["message"]["content"]
                    STATS["total_requests"] += 1
                    STATS["total_tokens"] += upstream.get("usage", {}).get("total_tokens", 100)
                    STATS["recent_logs"].insert(0, {
                        "time": datetime.utcnow().strftime("%H:%M:%S"),
                        "type": "POST /v1/messages",
                        "model": req_model,
                        "status": "200 OK"
                    })
                    STATS["recent_logs"] = STATS["recent_logs"][:25]
                    self._send_json(200, {
                        "id": upstream.get("id", "msg_zai"),
                        "type": "message",
                        "role": "assistant",
                        "model": req_model,
                        "content": [{"type": "text", "text": text_out}],
                        "stop_reason": "end_turn",
                        "usage": upstream.get("usage", {"input_tokens": 50, "output_tokens": 50})
                    })
            except Exception as e:
                self._send_json(500, {"error": {"message": str(e)}})
            return

        # Handle OpenAI /v1/chat/completions
        if path in ("/v1/chat/completions", "/chat/completions"):
            body["model"] = "openai-fast"
            req = urllib.request.Request(
                UPSTREAM_URL,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "User-Agent": "zai2api-render"}
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as res:
                    res_bytes = res.read()
                    upstream = json.loads(res_bytes.decode("utf-8"))
                    STATS["total_requests"] += 1
                    STATS["total_tokens"] += upstream.get("usage", {}).get("total_tokens", 100)
                    STATS["recent_logs"].insert(0, {
                        "time": datetime.utcnow().strftime("%H:%M:%S"),
                        "type": "POST /v1/chat/completions",
                        "model": req_model,
                        "status": "200 OK"
                    })
                    STATS["recent_logs"] = STATS["recent_logs"][:25]
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
                    self.wfile.write(res_bytes)
            except Exception as e:
                self._send_json(500, {"error": {"message": str(e)}})
            return

        self._send_json(404, {"error": {"message": f"Endpoint not found: {path}"}})

    def log_message(self, format, *args):
        pass

def main():
    server = HTTPServer(("0.0.0.0", PORT), ZaiProxyHandler)
    print(f"Z.ai2api server running on port {PORT}")
    server.serve_forever()

if __name__ == "__main__":
    main()
