"""NICO Cloud API server — FastAPI-based web interface for cloud deployment."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

try:
    from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
    from fastapi.responses import HTMLResponse, JSONResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError as e:
    msg = (
        "Missing FastAPI / uvicorn. Install with: pip install nico[web]"
    )
    raise ImportError(msg) from e

from nico.app import NicoApp
from nico.config.settings import Settings


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


# ---------------------------------------------------------------------------
# HTML template (embedded — no external files needed)
# ---------------------------------------------------------------------------

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NICO — Cloud Assistant</title>
<style>
  *{margin:0;padding:0;box-sizing:border-box}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
       background:#0f0f1a;color:#e0e0e0;height:100vh;display:flex;flex-direction:column}
  #header{background:#1a1a2e;padding:14px 24px;border-bottom:1px solid #2a2a4a;
          display:flex;align-items:center;gap:12px;flex-shrink:0}
  #header h1{font-size:20px;font-weight:700;color:#e94560;letter-spacing:1px}
  #header .sub{font-size:12px;color:#666;margin-left:auto}
  .dot{width:8px;height:8px;border-radius:50%;background:#4ade80;display:inline-block;animation:pulse 2s infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
  #chat{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:10px}
  .msg{max-width:82%;padding:10px 16px;border-radius:12px;line-height:1.5;word-wrap:break-word;animation:fadeIn .2s}
  .user{background:#1e3a5f;align-self:flex-end;border-bottom-right-radius:4px}
  .nico{background:#1a1a2e;align-self:flex-start;border-bottom-left-radius:4px;border:1px solid #2a2a4a}
  .nico .label{font-size:10px;color:#e94560;margin-bottom:3px;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
  .error{background:#3d0000;align-self:flex-start;border-bottom-left-radius:4px;border:1px solid #6b0000}
  #input-area{display:flex;gap:8px;padding:16px 24px;background:#1a1a2e;
              border-top:1px solid #2a2a4a;flex-shrink:0}
  #input{flex:1;padding:12px 16px;border-radius:8px;border:1px solid #2a2a4a;
         background:#0f0f1a;color:#e0e0e0;font-size:14px;outline:none;transition:border-color .2s}
  #input:focus{border-color:#e94560}
  #send{padding:12px 28px;border-radius:8px;border:none;background:#e94560;
        color:#fff;font-size:14px;font-weight:600;cursor:pointer;transition:background .2s}
  #send:hover{background:#d63851}
  #send:disabled{opacity:.5;cursor:not-allowed}
  .mic-btn{padding:12px 16px;border-radius:8px;border:1px solid #2a2a4a;
           background:#1a1a2e;color:#e0e0e0;font-size:18px;cursor:pointer;transition:all .2s}
  .mic-btn:hover{background:#2a2a4a}
  .toggle-label{display:flex;align-items:center;gap:6px;cursor:pointer;font-size:12px;color:#888}
  .toggle-label input{accent-color:#e94560}
  .toggle-text{user-select:none}
  @keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
  .typing{color:#666;font-size:13px;padding:8px 16px;font-style:italic}
  ::-webkit-scrollbar{width:6px}
  ::-webkit-scrollbar-track{background:#0f0f1a}
  ::-webkit-scrollbar-thumb{background:#2a2a4a;border-radius:3px}
  .actions{display:flex;gap:8px;padding:0 24px 8px;flex-shrink:0}
  .actions button{padding:6px 14px;border-radius:6px;border:1px solid #2a2a4a;
                   background:transparent;color:#888;font-size:12px;cursor:pointer}
  .actions button:hover{background:#1a1a2e;color:#e0e0e0}
  pre{white-space:pre-wrap;font-family:inherit}
</style>
</head>
<body>
<div id="header">
  <span class="dot" id="statusDot"></span>
  <h1>NICO</h1>
  <span class="sub" id="status">cloud</span>
</div>
<div class="actions">
  <button onclick="clearChat()">Clear</button>
  <label class="toggle-label">
    <input type="checkbox" id="wakeToggle" onchange="toggleWake()">
    <span class="toggle-text">Wake: OFF</span>
  </label>
</div>
<div id="chat">
  <div class="msg nico"><div class="label">NICO</div>Hello! I'm NICO. Say "NICO" to activate, or type a message.</div>
</div>
<div id="input-area">
  <input id="input" type="text" placeholder="Type or tap mic to speak..." autofocus>
  <button id="micBtn" class="mic-btn" onclick="pushToTalk()" title="Click and speak">🎤</button>
  <button id="send" onclick="send()">Send</button>
</div>
<script>
  const chat=document.getElementById('chat'), input=document.getElementById('input'), sendBtn=document.getElementById('send');
  const micBtn=document.getElementById('micBtn'), wakeToggle=document.getElementById('wakeToggle');
  const statusDot=document.getElementById('statusDot'), statusText=document.getElementById('status');
  let ws=null, reconnectTimer=null, wakeRec=null, wakeActive=false, micActive=false;
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;

  // ---- Wake word detection ----
  function toggleWake(){
    if(!SR){ addMsg('nico','Speech recognition not supported in this browser.',true); wakeToggle.checked=false; return }
    if(wakeToggle.checked){
      wakeActive=true;
      document.querySelector('.toggle-text').textContent='Wake: ON';
      addMsg('nico','Wake word active — say "NICO" then your command.');
      startWake();
    }else{
      wakeActive=false;
      document.querySelector('.toggle-text').textContent='Wake: OFF';
      if(wakeRec) try{ wakeRec.stop() }catch(e){}
      setStatus('idle');
    }
  }

  function startWake(){
    if(!wakeActive||!SR) return;
    wakeRec=new SR();
    wakeRec.lang='en-US';
    wakeRec.continuous=true;
    wakeRec.interimResults=true;
    wakeRec.onresult=function(e){
      for(let i=e.resultIndex;i<e.results.length;i++){
        const r=e.results[i];
        if(!r.isFinal) continue;
        const text=r[0].transcript.toLowerCase().trim();
        if(text.includes('nico')){
          let cmd=text.split('nico')[1].trim();
          if(!cmd) cmd=''; // just wake word said
          if(cmd){
            setStatus('listening');
            addMsg('user','🎤 '+cmd);
            wakeRec.stop();
            sendRaw(cmd);
            if(wakeActive) setTimeout(startWake,500);
          }else{
            setStatus('awake');
            // Listen for next utterance as command
            wakeRec.stop();
            const cmdRec=new SR();
            cmdRec.lang='en-US';
            cmdRec.interimResults=false;
            cmdRec.onresult=function(ev){
              const c=ev.results[0][0].transcript;
              setStatus('listening');
              addMsg('user','🎤 '+c);
              sendRaw(c);
              if(wakeActive) setTimeout(startWake,500);
            };
            cmdRec.onend=function(){ if(wakeActive) setTimeout(startWake,100) };
            try{ cmdRec.start() }catch(e){}
          }
          break;
        }
      }
    };
    wakeRec.onend=function(){ if(wakeActive) setTimeout(startWake,100) };
    try{ wakeRec.start(); setStatus('wake-active') }catch(e){}
  }

  // ---- Push-to-talk ----
  function pushToTalk(){
    if(!SR){ addMsg('nico','Speech recognition not supported.',true); return }
    if(micActive) return;
    micActive=true;
    micBtn.textContent='🔴';
    setStatus('listening');
    const rec=new SR();
    rec.lang='en-US';
    rec.interimResults=false;
    rec.onresult=function(e){
      const text=e.results[0][0].transcript;
      addMsg('user','🎤 '+text);
      sendRaw(text);
    };
    rec.onend=function(){ micActive=false; micBtn.textContent='🎤'; setStatus(wakeActive?'wake-active':'idle') };
    rec.onerror=function(){ micActive=false; micBtn.textContent='🎤'; setStatus(wakeActive?'wake-active':'idle') };
    try{ rec.start() }catch(e){ micActive=false; micBtn.textContent='🎤' }
  }

  // ---- Core send ----
  async function sendRaw(msg){
    if(!msg.trim()) return;
    sendBtn.disabled=true;
    const typing=document.createElement('div');
    typing.className='typing'; typing.textContent='NICO is thinking...';
    chat.appendChild(typing);
    try{
      if(ws&&ws.readyState===WebSocket.OPEN){
        ws.send(JSON.stringify({message:msg}));
        sendBtn.disabled=false;
        typing.remove();
      }else{
        const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
        const d=await r.json();
        typing.remove();
        addMsg('nico',d.response||d.error||'No response');
        if(d.error) addMsg('nico','Check server logs.',true);
      }
    }catch(e){ typing.remove(); addMsg('nico','Connection error.',true) }
    sendBtn.disabled=false;
  }

  async function send(){
    const msg=input.value.trim();
    if(!msg) return;
    input.value=''; addMsg('user',msg); sendBtn.disabled=true;
    const typing=document.createElement('div');
    typing.className='typing'; typing.textContent='NICO is thinking...';
    chat.appendChild(typing);
    try{
      if(ws&&ws.readyState===WebSocket.OPEN){
        ws.send(JSON.stringify({message:msg}));
        sendBtn.disabled=false; input.focus(); typing.remove();
      }else{
        const r=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg})});
        const d=await r.json();
        typing.remove();
        addMsg('nico',d.response||d.error||'No response');
        if(d.error) addMsg('nico','Check server logs.',true);
      }
    }catch(e){ typing.remove(); addMsg('nico','Connection error.',true) }
    sendBtn.disabled=false; input.focus();
  }

  function setStatus(s){
    statusDot.className='dot';
    const labels={'idle':'connected','wake-active':'wake on','awake':'NICO?','listening':'listening...','reconnecting':'reconnecting...'};
    statusText.textContent=labels[s]||s;
    if(s==='listening') statusDot.style.background='#f59e0b';
    else if(s==='awake') statusDot.style.background='#3b82f6';
    else if(s==='wake-active') statusDot.style.background='#4ade80';
    else statusDot.style.background='#4ade80';
  }

  // ---- WebSocket ----
  function connectWS(){
    const proto=location.protocol==='https:'?'wss:':'ws:';
    const url=proto+'//'+location.host+'/ws';
    if(ws) try{ws.close()}catch(_){}
    ws=new WebSocket(url);
    ws.onopen=()=>{setStatus(wakeActive?'wake-active':'idle')};
    ws.onmessage=e=>{
      const typing=document.querySelector('.typing');
      if(typing) typing.remove();
      try{
        const d=JSON.parse(e.data);
        if(d.type==='token'){addMsg('nico',d.text)}
        else if(d.type=='done'){}
      }catch(_){addMsg('nico',e.data)}
    };
    ws.onclose=()=>{setStatus('reconnecting'); reconnectTimer=setTimeout(connectWS,3000)};
    ws.onerror=()=>{ws.close()};
  }

  input.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}});
  function addMsg(sender,text,isErr){
    const d=document.createElement('div');
    d.className='msg '+(isErr?'error':sender);
    if(sender==='nico') d.innerHTML='<div class="label">NICO</div>'+escapeHtml(text);
    else d.textContent=text;
    chat.appendChild(d); chat.scrollTop=chat.scrollHeight;
  }
  function escapeHtml(t){return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
  function clearChat(){chat.innerHTML='';addMsg('nico','Chat cleared.')}
  connectWS();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app: FastAPI | None = None
_nico: NicoApp | None = None

# In-memory store for connected devices
_device_sensors: dict[str, dict[str, Any]] = {}
_device_commands: dict[str, list[dict[str, Any]]] = {}
_command_counter: int = 0

CLOUD_API_KEY = os.getenv("NICO_CLOUD_API_KEY", "")


async def verify_auth(authorization: str | None = Header(None)) -> None:
    """FastAPI dependency: raise 401 if CLOUD_API_KEY is set and header is wrong."""
    if CLOUD_API_KEY and authorization != f"Bearer {CLOUD_API_KEY}":
        raise HTTPException(401, "Unauthorized")


@asynccontextmanager
async def _lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown lifecycle."""
    global _nico
    settings = Settings.from_env()
    _nico = NicoApp(settings=settings)
    await _nico.lifecycle.start()
    yield
    await _nico.lifecycle.stop()


def create_app() -> FastAPI:
    """Factory to create the FastAPI application."""
    global app
    _app = FastAPI(
        title="NICO Cloud API",
        version="0.2.0",
        lifespan=_lifespan,
    )

    @_app.get("/", response_class=HTMLResponse)
    async def index() -> str:
        return HTML_PAGE

    @_app.post("/api/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest) -> dict[str, str]:
        if _nico is None:
            raise HTTPException(503, "NICO not initialized")
        response = await _nico.chat(req.message)
        return {"response": response}

    @_app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "initialized": _nico is not None,
        }

    @_app.get("/api/devices")
    async def list_devices(auth: None = Depends(verify_auth)) -> list[str]:
        return list(_device_sensors.keys())

    @_app.post("/api/devices/{device_id}/sensors")
    async def post_sensors(
        device_id: str, data: dict[str, Any], auth: None = Depends(verify_auth)
    ) -> dict[str, str]:
        _device_sensors[device_id] = data
        return {"status": "ok"}

    @_app.get("/api/devices/{device_id}/sensors")
    async def get_sensors(device_id: str) -> dict[str, Any]:
        return _device_sensors.get(device_id, {})

    @_app.get("/api/devices/{device_id}/commands")
    async def get_commands(
        device_id: str, auth: None = Depends(verify_auth)
    ) -> dict[str, list[dict[str, Any]]]:
        cmds = _device_commands.get(device_id, [])
        _device_commands[device_id] = []
        return {"commands": cmds}

    @_app.post("/api/devices/{device_id}/commands")
    async def send_command(
        device_id: str, cmd: dict[str, Any]
    ) -> dict[str, str]:
        global _command_counter
        _command_counter += 1
        cmd["id"] = str(_command_counter)
        _device_commands.setdefault(device_id, []).append(cmd)
        return {"status": "queued", "command_id": str(_command_counter)}

    @_app.post("/api/devices/{device_id}/commands/{command_id}/result")
    async def command_result(
        device_id: str, command_id: str, result: dict[str, Any]
    ) -> dict[str, str]:
        _device_sensors.setdefault(device_id, {})[f"cmd_{command_id}_result"] = result
        return {"status": "ok"}

    @_app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                data = await websocket.receive_json()
                message = data.get("message", "")
                if _nico is None:
                    await websocket.send_json({"error": "NICO not initialized"})
                    continue
                response = await _nico.chat(message)
                await websocket.send_json({"response": response})
        except WebSocketDisconnect:
            pass
        except Exception as exc:
            try:
                await websocket.send_json({"error": str(exc)})
            except Exception:
                pass

    return _app


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the server via: python -m nico.web_api"""
    port = int(os.getenv("NICO_PORT", "8080"))
    host = os.getenv("NICO_HOST", "0.0.0.0")

    application = create_app()

    print(f"")
    print(f"  ╔══════════════════════════════════════╗")
    print(f"  ║     NICO Cloud Server                ║")
    print(f"  ║                                      ║")
    print(f"  ║  Listening on {host}:{port}                ║")
    print(f"  ║  Open http://localhost:{port}               ║")
    print(f"  ║  Press Ctrl+C to stop                ║")
    print(f"  ╚══════════════════════════════════════╝")
    print(f"")

    uvicorn.run(application, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
