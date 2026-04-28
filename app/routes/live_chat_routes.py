"""
Live Chat REST endpoints  (ported from WheBot FastAPI backend)
Prefix: /py/api/live

Endpoints
---------
POST   /new-user-lead      – website visitor submits enquiry form
POST   /client-support     – existing client submits support ticket
GET    /chats              – admin dashboard: list all chat sessions
GET    /chats/<chat_id>    – fetch single chat with full message history
PATCH  /chats/<chat_id>/close  – close a chat session
"""

from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from bson import ObjectId

from ..db import mongo
from ..config import API_KEY_SECRET
from app import socketio   # shared SocketIO instance

live_chat_bp = Blueprint("live_chat", __name__)

# ─────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def msg_obj(sender: str, text: str) -> dict:
    return {"sender": sender, "text": text, "ts": now_iso()}


def serialize(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


# ─────────────────────────────────────────
#  API-key guard
# ─────────────────────────────────────────

@live_chat_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return "", 200
    # Skip key check for GET /chats (agent dashboard uses JWT separately)
    # For POST endpoints, enforce x-api-key
    if request.method == "POST":
        key = request.headers.get("x-api-key", "")
        if API_KEY_SECRET and key != API_KEY_SECRET:
            return jsonify({"error": "Unauthorized"}), 401


# ─────────────────────────────────────────
#  POST /new-user-lead
# ─────────────────────────────────────────

@live_chat_bp.route("/new-user-lead", methods=["POST", "OPTIONS"])
def new_user_lead():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json(force=True, silent=True) or {}

    required = ["userType", "service", "name", "mobile", "email", "address"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Save lead
    lead_doc = {
        "userType":        data["userType"],
        "service":         data["service"],
        "subRequirement":  data.get("subRequirement", ""),
        "requirement":     data.get("requirement", ""),
        "name":            data["name"],
        "mobile":          data["mobile"],
        "email":           data["email"],
        "address":         data["address"],
        "createdAt":       now_iso(),
    }
    lead_result = mongo.db.live_leads.insert_one(lead_doc)

    # Create live chat session
    chat_doc = {
        "type":       "new_user",
        "status":     "open",
        "name":       data["name"],
        "email":      data["email"],
        "mobile":     data["mobile"],
        "service":    data["service"],
        "lead_id":    str(lead_result.inserted_id),
        "messages":   [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    chat_result = mongo.db.live_chats.insert_one(chat_doc)
    chat_id = str(chat_result.inserted_id)

    # Notify agent dashboard via Socket.IO
    socketio.emit("new_chat", {
        "chat_id":    chat_id,
        "name":       data["name"],
        "service":    data["service"],
        "type":       "new_user",
        "status":     "open",
        "created_at": chat_doc["created_at"],
    })

    return jsonify({"chat_id": chat_id}), 201


# ─────────────────────────────────────────
#  POST /client-support
# ─────────────────────────────────────────

@live_chat_bp.route("/client-support", methods=["POST", "OPTIONS"])
def client_support():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json(force=True, silent=True) or {}

    required = ["company", "issue", "email", "mobile"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Missing field: {field}"}), 400

    support_doc = {**data, "created_at": now_iso()}
    support_result = mongo.db.live_support.insert_one(support_doc)

    chat_doc = {
        "type":       "client",
        "status":     "open",
        "name":       data["company"],
        "email":      data["email"],
        "mobile":     data["mobile"],
        "service":    "Support",
        "issue":      data["issue"],
        "support_id": str(support_result.inserted_id),
        "messages":   [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    chat_result = mongo.db.live_chats.insert_one(chat_doc)
    chat_id = str(chat_result.inserted_id)

    socketio.emit("new_chat", {
        "chat_id":    chat_id,
        "name":       data["company"],
        "service":    "Support",
        "type":       "client",
        "status":     "open",
        "created_at": chat_doc["created_at"],
    })

    return jsonify({"chat_id": chat_id}), 201


# ─────────────────────────────────────────
#  GET /chats
# ─────────────────────────────────────────

@live_chat_bp.route("/chats", methods=["GET"])
def get_all_chats():
    chats = list(mongo.db.live_chats.find({}).sort("updated_at", -1))
    return jsonify([serialize(c) for c in chats])


# ─────────────────────────────────────────
#  GET /chats/<chat_id>
# ─────────────────────────────────────────

@live_chat_bp.route("/chats/<chat_id>", methods=["GET"])
def get_chat(chat_id: str):
    try:
        doc = mongo.db.live_chats.find_one({"_id": ObjectId(chat_id)})
    except Exception:
        return jsonify({"error": "Invalid chat_id"}), 400

    if not doc:
        return jsonify({"error": "Chat not found"}), 404

    return jsonify(serialize(doc))


# ─────────────────────────────────────────
#  PATCH /chats/<chat_id>/close
# ─────────────────────────────────────────

@live_chat_bp.route("/chats/<chat_id>/close", methods=["PATCH"])
def close_chat(chat_id: str):
    try:
        mongo.db.live_chats.update_one(
            {"_id": ObjectId(chat_id)},
            {"$set": {"status": "closed", "updated_at": now_iso()}}
        )
    except Exception:
        return jsonify({"error": "Invalid chat_id"}), 400

    socketio.emit("chat_closed", {"chat_id": chat_id})
    return jsonify({"ok": True})
