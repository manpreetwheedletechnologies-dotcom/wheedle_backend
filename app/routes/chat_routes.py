from flask import Blueprint, request, jsonify
from app.services.ai_service import generate_ai_response
from app.services.guardrails_service import is_blocked
from app.data.static_responses import company_responses
from app.config import API_KEY_SECRET

chat_bp = Blueprint("chat", __name__)

@chat_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return "", 200

    api_key = request.headers.get("x-api-key")
    if api_key != API_KEY_SECRET:
        return jsonify({"reply": "Unauthorized", "success": False}), 401


@chat_bp.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    data = request.get_json(silent=True) or {}
    user_input = data.get("message", "").strip()

    if not user_input:
        return jsonify({"reply": "Please enter a message.", "success": False})

    if is_blocked(user_input):
        return jsonify({"reply": "This request is not allowed.", "success": False})

    lower_input = user_input.lower()

    for key, value in company_responses.items():
        if key in lower_input:
            return jsonify({"reply": value, "success": True})

    answer = generate_ai_response(user_input)

    return jsonify({"reply": answer, "success": True})
