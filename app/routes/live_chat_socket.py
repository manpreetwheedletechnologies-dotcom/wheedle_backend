"""
live_chat_socket.py
Flask-SocketIO handlers for live chat functionality.

FIX: Handlers are now at module level so they register when imported.
     (Previously wrapped in init_socketio() which was never called.)
"""

from flask import request
from flask_socketio import emit, join_room, leave_room
from datetime import datetime
from app import socketio
from ..db import mongo


def now_iso():
    return datetime.utcnow().isoformat() + "Z"


@socketio.on("connect")
def handle_connect():
    print(f"[SOCKET] Client connected: {request.sid}")
    emit("connected", {"sid": request.sid})


@socketio.on("disconnect")
def handle_disconnect():
    print(f"[SOCKET] Client disconnected: {request.sid}")


@socketio.on("join_chat")
def handle_join_chat(data):
    """Join a chat room. Both user and agent join the same room."""
    chat_id = data.get("chat_id")
    role = data.get("role", "user")

    if not chat_id:
        print("[SOCKET] join_chat: No chat_id provided")
        return

    join_room(chat_id)
    print(f"[SOCKET] {role} joined room: {chat_id}")

    # Notify agent that user has joined (and vice versa)
    emit("user_joined", {
        "chat_id": chat_id,
        "role": role,
        "sid": request.sid
    }, room=chat_id, include_self=False)

    # If agent is joining, notify user via agent_connected event
    if role == "agent":
        try:
            from bson import ObjectId
            mongo.db.live_chats.update_one(
                {"_id": ObjectId(chat_id)},
                {"$set": {"agent_joined": True}}
            )
        except Exception:
            pass
        emit("agent_connected", {
            "chat_id": chat_id,
            "ts": now_iso()
        }, room=chat_id, include_self=False)
        print(f"[SOCKET] agent_connected sent to room: {chat_id}")


@socketio.on("leave_chat")
def handle_leave_chat(data):
    """Leave a chat room."""
    chat_id = data.get("chat_id")
    if chat_id:
        leave_room(chat_id)
        print(f"[SOCKET] Client left room: {chat_id}")


@socketio.on("user_message")
def handle_user_message(data):
    """
    Handle messages from WheBot (user side).
    Broadcasts to agent dashboard.
    """
    chat_id = data.get("chat_id")
    text = data.get("text", "")

    if not chat_id or not text:
        print("[SOCKET] user_message: Missing chat_id or text")
        return

    msg = {
        "sender": "user",
        "text": text,
        "ts": now_iso()
    }

    # Save to correct collection: live_chats (not 'chats')
    try:
        from bson import ObjectId
        mongo.db.live_chats.update_one(
            {"_id": ObjectId(chat_id)},
            {
                "$push": {"messages": msg},
                "$set": {"updated_at": msg["ts"]}
            }
        )
    except Exception as e:
        print(f"[SOCKET] DB error saving user_message: {e}")

    print(f"[SOCKET] User message saved in room {chat_id}: {text[:50]}")

    # Broadcast to ALL clients in room (agent receives it)
    emit("new_message", {
        "chat_id": chat_id,
        "sender": "user",
        "text": text,
        "ts": msg["ts"]
    }, room=chat_id)


@socketio.on("agent_message")
def handle_agent_message(data):
    """
    Handle messages from agent dashboard.
    Broadcasts to WheBot (user side).
    """
    chat_id = data.get("chat_id")
    text = data.get("text", "")

    if not chat_id or not text:
        print("[SOCKET] agent_message: Missing chat_id or text")
        return

    msg = {
        "sender": "agent",
        "text": text,
        "ts": now_iso()
    }

    # Save to correct collection: live_chats (not 'chats')
    try:
        from bson import ObjectId
        mongo.db.live_chats.update_one(
            {"_id": ObjectId(chat_id)},
            {
                "$push": {"messages": msg},
                "$set": {
                    "updated_at": msg["ts"],
                    "agent_joined": True
                }
            }
        )
    except Exception as e:
        print(f"[SOCKET] DB error saving agent_message: {e}")

    print(f"[SOCKET] Agent message broadcast to room {chat_id}: {text[:50]}")

    # Broadcast to ALL clients in room (user/bot receives it)
    emit("new_message", {
        "chat_id": chat_id,
        "sender": "agent",
        "text": text,
        "ts": msg["ts"]
    }, room=chat_id)


@socketio.on("agent_join")
def handle_agent_join(data):
    """Notify user when an agent explicitly joins the chat."""
    chat_id = data.get("chat_id")
    if not chat_id:
        return

    try:
        from bson import ObjectId
        mongo.db.live_chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"agent_joined": True}}
        )
    except Exception:
        pass

    emit("agent_connected", {
        "chat_id": chat_id,
        "ts": now_iso()
    }, room=chat_id)

    print(f"[SOCKET] Agent joined notification sent to room: {chat_id}")


@socketio.on("close_chat")
def handle_close_chat(data):
    """Close a chat session."""
    chat_id = data.get("chat_id")
    if not chat_id:
        return

    try:
        from bson import ObjectId
        mongo.db.live_chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"status": "closed", "updated_at": now_iso()}}
        )
    except Exception:
        pass

    emit("chat_closed", {
        "chat_id": chat_id,
        "ts": now_iso()
    }, room=chat_id)

    print(f"[SOCKET] Chat closed: {chat_id}")


@socketio.on("typing")
def handle_typing(data):
    """Handle typing indicator."""
    chat_id = data.get("chat_id")
    role = data.get("role", "user")
    is_typing = data.get("is_typing", False)

    if not chat_id:
        return

    emit("typing", {
        "chat_id": chat_id,
        "role": role,
        "is_typing": is_typing
    }, room=chat_id, include_self=False)