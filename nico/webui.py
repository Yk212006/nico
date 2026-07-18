"""NICO Web Interface — access from any browser on your network."""

from __future__ import annotations

import asyncio
import json
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Any

HOST = "0.0.0.0"
PORT = int(os.getenv("NICO_WEB_PORT", "8080"))

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NICO Assistant</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
         background: #1a1a2e; color: #e0e0e0; height: 100vh; display: flex;
         flex-direction: column; }
  #header { background: #16213e; padding: 16px 24px; border-bottom: 1px solid #0f3460;
            display: flex; align-items: center; gap: 12px; }
  #header h1 { font-size: 20px; font-weight: 600; color: #e94560; }
  #header .status { font-size: 12px; color: #888; }
  #header .dot { width: 8px; height: 8px; border-radius: 50%; background: #4ade80;
                 display: inline-block; }
  #chat { flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column;
          gap: 12px; }
  .msg { max-width: 80%; padding: 12px 16px; border-radius: 12px; line-height: 1.5;
         word-wrap: break-word; animation: fadeIn 0.2s; }
  .user { background: #0f3460; align-self: flex-end; border-bottom-right-radius: 4px; }
  .nico { background: #16213e; align-self: flex-start; border-bottom-left-radius: 4px; }
  .nico .label { font-size: 11px; color: #e94560; margin-bottom: 4px; font-weight: 600; }
  .error { background: #3d0000; align-self: flex-start; border-bottom-left-radius: 4px; }
  #input-area { display: flex; gap: 8px; padding: 16px 24px; background: #16213e;
                border-top: 1px solid #0f3460; }
  #input { flex: 1; padding: 12px 16px; border-radius: 8px; border: 1px solid #0f3460;
           background: #1a1a2e; color: #e0e0e0; font-size: 14px; outline: none; }
  #input:focus { border-color: #e94560; }
  #send { padding: 12px 24px; border-radius: 8px; border: none; background: #e94560;
          color: white; font-size: 14px; font-weight: 600; cursor: pointer;
          transition: background 0.2s; }
  #send:hover { background: #d63851; }
  #send:disabled { opacity: 0.5; cursor: not-allowed; }
  @keyframes fadeIn { from { opacity: 0; transform: translateY(8px); }
                       to { opacity: 1; transform: translateY(0); } }
  .typing { color: #888; font-size: 13px; padding: 8px 16px; }
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #1a1a2e; }
  ::-webkit-scrollbar-thumb { background: #0f3460; border-radius: 3px; }
</style>
</head>
<body>
<div id="header">
  <span class="dot"></span>
  <h1>NICO</h1>
  <span class="status">connected</span>
</div>
<div id="chat">
  <div class="msg nico"><div class="label">NICO</div>Hello! I'm NICO. Ask me anything.</div>
</div>
<div id="input-area">
  <input id="input" type="text" placeholder="Type a message..." autofocus>
  <button id="send" onclick="send()">Send</button>
</div>
<script>
  const chat = document.getElementById('chat');
  const input = document.getElementById('input');
  const sendBtn = document.getElementById('send');

  input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });

  function addMsg(sender, text, isError) {
    const div = document.createElement('div');
    div.className = 'msg ' + (isError ? 'error' : sender);
    if (sender === 'nico') div.innerHTML = '<div class="label">NICO</div>' + escapeHtml(text);
    else div.textContent = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
  }

  function escapeHtml(t) {
    return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  async function send() {
    const msg = input.value.trim();
    if (!msg) return;
    if (msg.toLowerCase() === 'exit' || msg.toLowerCase() === 'quit')
      return addMsg('nico', 'Goodbye! Close the tab or type another message.');

    input.value = '';
    addMsg('user', msg);
    sendBtn.disabled = true;

    const typing = document.createElement('div');
    typing.className = 'typing';
    typing.textContent = 'NICO is thinking...';
    chat.appendChild(typing);

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });
      const data = await resp.json();
      typing.remove();
      addMsg('nico', data.response || data.error || 'No response');
    } catch (e) {
      typing.remove();
      addMsg('nico', 'Connection error. Is the server still running?', true);
    }
    sendBtn.disabled = false;
    input.focus();
  }
</script>
</body>
</html>"""


class _Handler(SimpleHTTPRequestHandler):
    app: Any = None

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/api/chat":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            msg = data.get("message", "")

            if self.app is None:
                response = "NICO is not initialized yet."
            else:
                try:
                    future = asyncio.run_coroutine_threadsafe(
                        self.app.chat(msg), _loop
                    )
                    result = future.result(timeout=60)
                    response = str(result)
                except Exception as exc:
                    response = f"Error: {exc}"

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps({"response": response}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_: Any) -> None:
        pass


_loop: asyncio.AbstractEventLoop | None = None


def _start_worker(app: Any) -> None:
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


def main() -> None:
    from nico.app import NicoApp
    from nico.config.settings import Settings

    settings = Settings.from_env()
    app = NicoApp(settings=settings)

    _Handler.app = app
    server = HTTPServer((HOST, PORT), _Handler)

    print(f"")
    print(f"  ╔══════════════════════════════════════╗")
    print(f"  ║     NICO Web Interface               ║")
    print(f"  ║                                      ║")
    print(f"  ║  Open in your browser:               ║")
    print(f"  ║  http://localhost:{PORT}                 ║")
    print(f"  ║  or http://<pi-ip>:{PORT}                ║")
    print(f"  ║                                      ║")
    print(f"  ║  Press Ctrl+C to stop                ║")
    print(f"  ╚══════════════════════════════════════╝")
    print(f"")

    t = threading.Thread(target=_start_worker, args=(app,), daemon=True)
    t.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
