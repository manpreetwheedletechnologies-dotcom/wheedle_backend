# Wheedle Backend — Integrated Live Chat

## What was added

The **WheBot real-time agent chat** (originally a separate FastAPI + Socket.IO server) is now
fully integrated into this Flask backend.

### New files
| File | Purpose |
|---|---|
| `app/routes/live_chat_routes.py` | REST endpoints for live chat (create sessions, list chats, close) |
| `app/routes/live_chat_socket.py` | All Socket.IO event handlers |

### Changed files
| File | Change |
|---|---|
| `app/__init__.py` | Added `flask-socketio`, registers `live_chat_bp` and socket handlers |
| `run.py` | Now uses `socketio.run()` instead of `app.run()` |
| `requirements.txt` | Added `flask-socketio` |

---

## Live Chat API endpoints  (`/py/api/live/`)

### REST

| Method | Path | Description |
|---|---|---|
| POST | `/py/api/live/new-user-lead` | Visitor submits enquiry; creates a chat session |
| POST | `/py/api/live/client-support` | Client submits support ticket; creates a chat session |
| GET  | `/py/api/live/chats` | List all chat sessions (agent dashboard) |
| GET  | `/py/api/live/chats/<id>` | Get single chat with full message history |
| PATCH | `/py/api/live/chats/<id>/close` | Close a chat session |

### Socket.IO events

**Client → Server**

| Event | Payload | Description |
|---|---|---|
| `join_chat` | `{ chat_id, role }` | Join a chat room. `role` = `"user"` or `"agent"` |
| `user_message` | `{ chat_id, text }` | Website visitor sends a message |
| `agent_message` | `{ chat_id, text }` | Agent replies |

**Server → Client**

| Event | Payload | Description |
|---|---|---|
| `new_chat` | `{ chat_id, name, service, type, status, created_at }` | Broadcast when a new chat session opens |
| `new_message` | `{ chat_id, sender, text, ts }` | Broadcast when any message is sent |
| `chat_closed` | `{ chat_id }` | Broadcast when a chat is closed |

---

## MongoDB collections

| Collection | Used by |
|---|---|
| `live_chats` | All live chat sessions + messages |
| `live_leads` | New-user enquiry form data |
| `live_support` | Client support ticket data |

---

## Running

```bash
pip install -r requirements.txt
python run.py
```

The server starts on `http://0.0.0.0:5000`.  
WebSocket connections go to the same port — no separate server needed.
