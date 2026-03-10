"""カスタマーサポートエージェント Web アプリケーション。

FastAPI + Server-Sent Events でチャット UI を提供する。
起動: python webapp.py
"""

import json
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from agent import create_project_client, create_agent
from main import handle_function_calls
from tools import TOOL_FUNCTIONS

# ---------------------------------------------------------------------------
# グローバル状態
# ---------------------------------------------------------------------------

_project = None
_openai = None
_agent = None

# セッションごとの previous_response_id を保持
_sessions: dict[str, str | None] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時にエージェントを作成し、終了時に削除する。"""
    global _project, _openai, _agent
    _project = create_project_client()
    _openai = _project.get_openai_client()
    _agent = create_agent(_project)
    yield


app = FastAPI(lifespan=lifespan)


# ---------------------------------------------------------------------------
# API エンドポイント
# ---------------------------------------------------------------------------


@app.post("/api/chat")
async def chat(request: Request):
    """ユーザーメッセージを受け取り、エージェントの応答を返す。"""
    body = await request.json()
    user_message = body.get("message", "").strip()
    session_id = body.get("session_id", "")

    if not user_message:
        return {"error": "メッセージが空です。"}

    if not session_id or session_id not in _sessions:
        session_id = str(uuid.uuid4())
        _sessions[session_id] = None

    previous_response_id = _sessions[session_id]

    # レスポンス生成
    kwargs: dict = {
        "input": [{"type": "message", "role": "user", "content": [{"type": "input_text", "text": user_message}]}],
        "extra_body": {
            "agent_reference": {"name": _agent.name, "type": "agent_reference"},
        },
    }
    if previous_response_id:
        kwargs["previous_response_id"] = previous_response_id

    response = _openai.responses.create(**kwargs)

    # Function Call ループ
    while True:
        tool_outputs = handle_function_calls(response)
        if not tool_outputs:
            break
        response = _openai.responses.create(
            input=tool_outputs,
            previous_response_id=response.id,
            extra_body={
                "agent_reference": {"name": _agent.name, "type": "agent_reference"},
            },
        )

    _sessions[session_id] = response.id

    return {
        "reply": response.output_text,
        "session_id": session_id,
    }


@app.post("/api/reset")
async def reset_session(request: Request):
    """セッションをリセットする。"""
    body = await request.json()
    session_id = body.get("session_id", "")
    if session_id in _sessions:
        del _sessions[session_id]
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def index():
    """チャット UI を返す。"""
    return _INDEX_HTML


# ---------------------------------------------------------------------------
# インライン HTML（単一ファイルで完結）
# ---------------------------------------------------------------------------

_INDEX_HTML = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>カスタマーサポート</title>
<style>
  :root {
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --bg: #f8fafc;
    --card: #ffffff;
    --border: #e2e8f0;
    --text: #1e293b;
    --text-light: #64748b;
    --user-bg: #2563eb;
    --user-text: #ffffff;
    --agent-bg: #f1f5f9;
    --agent-text: #1e293b;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                 "Helvetica Neue", Arial, "Noto Sans JP", sans-serif;
    background: var(--bg);
    color: var(--text);
    height: 100vh;
    display: flex;
    flex-direction: column;
  }

  header {
    background: var(--card);
    border-bottom: 1px solid var(--border);
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
  }

  header h1 {
    font-size: 18px;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  header h1::before {
    content: "🎧";
  }

  #reset-btn {
    background: none;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 13px;
    color: var(--text-light);
    cursor: pointer;
    transition: all 0.15s;
  }
  #reset-btn:hover {
    background: var(--bg);
    color: var(--text);
  }

  #chat-area {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .msg {
    max-width: 720px;
    width: fit-content;
    padding: 12px 16px;
    border-radius: 16px;
    line-height: 1.7;
    font-size: 14px;
    white-space: pre-wrap;
    word-wrap: break-word;
  }

  .msg.user {
    align-self: flex-end;
    background: var(--user-bg);
    color: var(--user-text);
    border-bottom-right-radius: 4px;
  }

  .msg.agent {
    align-self: flex-start;
    background: var(--agent-bg);
    color: var(--agent-text);
    border-bottom-left-radius: 4px;
  }

  .msg.agent strong { color: #0f172a; }

  .msg.system {
    align-self: center;
    background: transparent;
    color: var(--text-light);
    font-size: 13px;
  }

  .typing {
    align-self: flex-start;
    color: var(--text-light);
    font-size: 13px;
    padding: 8px 0;
  }
  .typing span {
    animation: blink 1.4s infinite both;
  }
  .typing span:nth-child(2) { animation-delay: 0.2s; }
  .typing span:nth-child(3) { animation-delay: 0.4s; }
  @keyframes blink {
    0%, 80%, 100% { opacity: 0.3; }
    40% { opacity: 1; }
  }

  #input-area {
    background: var(--card);
    border-top: 1px solid var(--border);
    padding: 16px 24px;
    display: flex;
    gap: 12px;
    flex-shrink: 0;
  }

  #msg-input {
    flex: 1;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 16px;
    font-size: 14px;
    font-family: inherit;
    outline: none;
    resize: none;
    min-height: 44px;
    max-height: 120px;
    transition: border-color 0.15s;
  }
  #msg-input:focus { border-color: var(--primary); }

  #send-btn {
    background: var(--primary);
    color: #fff;
    border: none;
    border-radius: 12px;
    padding: 0 20px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s;
    white-space: nowrap;
  }
  #send-btn:hover { background: var(--primary-hover); }
  #send-btn:disabled { opacity: 0.5; cursor: not-allowed; }

  .welcome {
    text-align: center;
    padding: 48px 24px;
    color: var(--text-light);
  }
  .welcome h2 { font-size: 20px; color: var(--text); margin-bottom: 8px; }
  .welcome p { font-size: 14px; line-height: 1.8; }
  .welcome .hints {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 20px;
    justify-content: center;
  }
  .welcome .hint {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 13px;
    cursor: pointer;
    transition: all 0.15s;
  }
  .welcome .hint:hover {
    background: var(--primary);
    color: #fff;
    border-color: var(--primary);
  }
</style>
</head>
<body>

<header>
  <h1>カスタマーサポート</h1>
  <button id="reset-btn" onclick="resetChat()">新しい会話</button>
</header>

<div id="chat-area">
  <div class="welcome">
    <h2>お問い合わせへようこそ</h2>
    <p>ご質問をお気軽にどうぞ。注文状況の確認・返品・製品情報など対応いたします。</p>
    <div class="hints">
      <div class="hint" onclick="sendHint(this)">注文 ORD-1001 の状況は？</div>
      <div class="hint" onclick="sendHint(this)">返品ポリシーを教えて</div>
      <div class="hint" onclick="sendHint(this)">PROD-001 の在庫はある？</div>
      <div class="hint" onclick="sendHint(this)">支払い方法は何がある？</div>
    </div>
  </div>
</div>

<div id="input-area">
  <textarea id="msg-input" rows="1" placeholder="メッセージを入力..."
    onkeydown="handleKey(event)"></textarea>
  <button id="send-btn" onclick="sendMessage()">送信</button>
</div>

<script>
  let sessionId = "";
  let busy = false;

  const chatArea = document.getElementById("chat-area");
  const msgInput = document.getElementById("msg-input");
  const sendBtn  = document.getElementById("send-btn");

  function addMessage(text, role) {
    // 初回送信時はウェルカムメッセージを消す
    const welcome = chatArea.querySelector(".welcome");
    if (welcome) welcome.remove();

    const div = document.createElement("div");
    div.className = "msg " + role;
    div.textContent = text;
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
    return div;
  }

  function showTyping() {
    const div = document.createElement("div");
    div.className = "typing";
    div.id = "typing";
    div.innerHTML = "<span>●</span><span>●</span><span>●</span> 回答を作成中...";
    chatArea.appendChild(div);
    chatArea.scrollTop = chatArea.scrollHeight;
  }

  function hideTyping() {
    const el = document.getElementById("typing");
    if (el) el.remove();
  }

  async function sendMessage() {
    const text = msgInput.value.trim();
    if (!text || busy) return;

    addMessage(text, "user");
    msgInput.value = "";
    msgInput.style.height = "auto";
    busy = true;
    sendBtn.disabled = true;
    showTyping();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: sessionId }),
      });
      const data = await res.json();
      hideTyping();

      if (data.error) {
        addMessage("エラー: " + data.error, "system");
      } else {
        sessionId = data.session_id;
        addMessage(data.reply, "agent");
      }
    } catch (e) {
      hideTyping();
      addMessage("通信エラーが発生しました。再度お試しください。", "system");
    } finally {
      busy = false;
      sendBtn.disabled = false;
      msgInput.focus();
    }
  }

  async function resetChat() {
    if (sessionId) {
      fetch("/api/reset", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      }).catch(() => {});
    }
    sessionId = "";
    chatArea.innerHTML = `
      <div class="welcome">
        <h2>お問い合わせへようこそ</h2>
        <p>ご質問をお気軽にどうぞ。注文状況の確認・返品・製品情報など対応いたします。</p>
        <div class="hints">
          <div class="hint" onclick="sendHint(this)">注文 ORD-1001 の状況は？</div>
          <div class="hint" onclick="sendHint(this)">返品ポリシーを教えて</div>
          <div class="hint" onclick="sendHint(this)">PROD-001 の在庫はある？</div>
          <div class="hint" onclick="sendHint(this)">支払い方法は何がある？</div>
        </div>
      </div>`;
    msgInput.focus();
  }

  function sendHint(el) {
    msgInput.value = el.textContent;
    sendMessage();
  }

  function handleKey(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  // テキストエリア自動リサイズ
  msgInput.addEventListener("input", () => {
    msgInput.style.height = "auto";
    msgInput.style.height = Math.min(msgInput.scrollHeight, 120) + "px";
  });
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8080)
