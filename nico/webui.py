"""NICO Web Interface — access from any browser on your network."""

from __future__ import annotations

import asyncio
import json
import os
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from typing import Any

from nico.config_profiles import load_profile

HOST = os.getenv("NICO_BIND_HOST", "127.0.0.1")
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
         background: #0f1115; color: #e8eaed; height: 100vh; display: flex;
         flex-direction: column; }
  #header { background: #11151c; padding: 14px 22px; border-bottom: 1px solid #232938;
            display: flex; align-items: center; justify-content: space-between; gap: 12px; }
  #header .left { display: flex; align-items: center; gap: 12px; }
  #header h1 { font-size: 18px; font-weight: 700; color: #f3f4f6; }
  #header .status { font-size: 12px; color: #8b95a7; }
  #header .dot { width: 8px; height: 8px; border-radius: 50%; background: #22c55e;
                 display: inline-block; }
  #chat-wrap { flex: 1; display: flex; justify-content: center; overflow: hidden; }
  #chat { width: min(860px, 100%); overflow-y: auto; padding: 22px 18px 28px; display: flex;
          flex-direction: column; gap: 14px; }
  .row { display: flex; width: 100%; gap: 12px; align-items: flex-start; }
  .row.user { justify-content: flex-end; }
  .avatar { width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center;
            flex: 0 0 auto; font-size: 12px; font-weight: 700; }
  .avatar.nico { background: #273449; color: #dbe7ff; }
  .avatar.user { background: #2563eb; color: white; }
  .bubble { max-width: min(82%, 740px); padding: 14px 16px; border-radius: 16px; line-height: 1.6;
            word-wrap: break-word; animation: fadeIn 0.2s; white-space: normal; }
  .bubble.user { background: #1f2937; border: 1px solid #2f3948; border-bottom-right-radius: 4px; }
  .bubble.nico { background: #141923; border: 1px solid #232938; border-bottom-left-radius: 4px; }
  .bubble.error { background: #2f1313; border: 1px solid #5a1f1f; }
  .bubble-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; margin-bottom: 8px; }
  .bubble .label { font-size: 11px; color: #9aa3b2; margin-bottom: 6px; font-weight: 700; }
  .copy-btn { border: 1px solid #2e3647; background: #0f131b; color: #cbd5e1; border-radius: 10px;
              padding: 6px 10px; font-size: 12px; cursor: pointer; }
  .copy-btn:hover { background: #18202b; }
  .bubble pre { margin: 10px 0; padding: 12px; border-radius: 10px; background: #0b1020; overflow-x: auto; }
  .bubble code { font-family: Consolas, 'Courier New', monospace; font-size: 13px; }
  .bubble .md-code { display: block; white-space: pre; }
  .bubble .md-inline { font-family: Consolas, 'Courier New', monospace; background: rgba(255,255,255,0.08); padding: 2px 5px; border-radius: 5px; }
  #composer { border-top: 1px solid #232938; background: #11151c; padding: 14px 16px; }
  #input-area { width: min(860px, 100%); margin: 0 auto; display: flex; gap: 10px; }
  #input { flex: 1; padding: 14px 16px; border-radius: 14px; border: 1px solid #2a3140;
           background: #0f131b; color: #e8eaed; font-size: 14px; outline: none; }
  #input:focus { border-color: #4f8cff; }
  #send { padding: 12px 18px; border-radius: 14px; border: none; background: #2563eb;
          color: white; font-size: 14px; font-weight: 700; cursor: pointer;
          transition: background 0.2s; }
  #send:hover { background: #1d4ed8; }
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
  <div class="left"><span class="dot"></span><h1>NICO</h1></div>
  <span class="status">offline chatbot</span>
</div>
<div id="chat-wrap"><div id="chat">
  <div class="row nico"><div class="avatar nico">N</div><div class="bubble nico"><div class="label">NICO</div>Hello! I'm NICO. Ask me anything.</div></div>
</div></div>
<div id="composer"><div id="input-area">
  <input id="input" type="text" placeholder="Message NICO..." autofocus>
  <button id="send" onclick="send()">Send</button>
</div></div>
<script>
  const chat = document.getElementById('chat');
  const input = document.getElementById('input');
  const sendBtn = document.getElementById('send');

  input.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });

  function createAssistantRow(text, isError) {
    const row = document.createElement('div');
    row.className = 'row nico';

    const avatar = document.createElement('div');
    avatar.className = 'avatar nico';
    avatar.textContent = 'N';

    const bubble = document.createElement('div');
    bubble.className = 'bubble ' + (isError ? 'error' : 'nico');
    bubble.dataset.raw = text;

    const head = document.createElement('div');
    head.className = 'bubble-head';

    const label = document.createElement('div');
    label.className = 'label';
    label.textContent = 'NICO';

    const copyBtn = document.createElement('button');
    copyBtn.className = 'copy-btn';
    copyBtn.type = 'button';
    copyBtn.textContent = 'Copy';
    copyBtn.onclick = async () => {
      try {
        await navigator.clipboard.writeText(bubble.dataset.raw || '');
        copyBtn.textContent = 'Copied';
        setTimeout(() => copyBtn.textContent = 'Copy', 1000);
      } catch (_) {}
    };

    const content = document.createElement('div');
    content.className = 'bubble-content';
    content.innerHTML = isError ? escapeHtml(text).replace(/\n/g, '<br>') : renderMarkdown(text);

    head.appendChild(label);
    head.appendChild(copyBtn);
    bubble.appendChild(head);
    bubble.appendChild(content);
    row.appendChild(avatar);
    row.appendChild(bubble);

    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;

    return { row, bubble, content };
  }

  function addMsg(sender, text, isError) {
    if (sender === 'nico') {
      createAssistantRow(text, isError);
      return;
    }

    const row = document.createElement('div');
    row.className = 'row user';

    const bubble = document.createElement('div');
    bubble.className = 'bubble user';
    bubble.textContent = text;

    const avatar = document.createElement('div');
    avatar.className = 'avatar user';
    avatar.textContent = 'Y';

    row.appendChild(bubble);
    row.appendChild(avatar);
    chat.appendChild(row);
    chat.scrollTop = chat.scrollHeight;
  }

  function escapeHtml(t) {
    return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  function renderMarkdown(text) {
    const lines = String(text).split(/\r?\n/);
    let out = '';
    let inCode = false;
    let codeLang = '';
    let codeLines = [];

    const flushParagraph = (paragraph) => {
      if (!paragraph.trim()) return '';
      return '<div>' + escapeHtml(paragraph)
        .replace(/`([^`]+)`/g, '<span class="md-inline">$1</span>')
        .replace(/\n/g, '<br>') + '</div>';
    };

    let paragraph = '';
    for (const line of lines) {
      const fence = line.match(/^```([a-zA-Z0-9_-]*)\s*$/);
      if (fence) {
        if (!inCode) {
          out += flushParagraph(paragraph);
          paragraph = '';
          inCode = true;
          codeLang = fence[1] || '';
          codeLines = [];
        } else {
          out += '<pre><code class="md-code lang-' + escapeHtml(codeLang) + '">' +
                 escapeHtml(codeLines.join('\n')) + '</code></pre>';
          inCode = false;
          codeLang = '';
          codeLines = [];
        }
        continue;
      }

      if (inCode) {
        codeLines.push(line);
      } else if (line.trim() === '') {
        out += flushParagraph(paragraph);
        paragraph = '';
      } else {
        paragraph += (paragraph ? '\n' : '') + line;
      }
    }

    if (inCode) {
      out += '<pre><code class="md-code lang-' + escapeHtml(codeLang) + '">' +
             escapeHtml(codeLines.join('\n')) + '</code></pre>';
    }
    out += flushParagraph(paragraph);
    return out || '<div>' + escapeHtml(text).replace(/\n/g, '<br>') + '</div>';
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
    typing.textContent = 'NICO is typing...';
    chat.appendChild(typing);

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg }),
      });
      const assistant = createAssistantRow('', false);
      typing.remove();
      const reader = resp.body?.getReader();
      if (!reader) {
        const text = await resp.text();
        assistant.bubble.dataset.raw = text;
        assistant.content.innerHTML = renderMarkdown(text);
      } else {
        let raw = '';
        const decoder = new TextDecoder();
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          raw += decoder.decode(value, { stream: true });
          assistant.bubble.dataset.raw = raw;
          assistant.content.innerHTML = '<div>' + escapeHtml(raw).replace(/\n/g, '<br>') + '</div>';
          chat.scrollTop = chat.scrollHeight;
        }
        assistant.content.innerHTML = renderMarkdown(raw);
      }
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

    profile_name = os.getenv("NICO_PROFILE", "local")
    try:
        profile = load_profile(profile_name)
    except Exception:
        profile = load_profile("local")

    settings = Settings(
        default_provider=profile["provider"],
        enable_tools=profile["enable_tools"],
        enable_memory=profile["enable_memory"],
    )
    app = NicoApp(settings=settings)

    _Handler.app = app
    server = HTTPServer((HOST, PORT), _Handler)

    print("")
    print("NICO Web Interface")
    print(f"Open: http://localhost:{PORT}")
    print("Ctrl+C to stop")
    print("")

    t = threading.Thread(target=_start_worker, args=(app,), daemon=True)
    t.start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
