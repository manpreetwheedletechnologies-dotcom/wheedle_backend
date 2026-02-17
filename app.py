import os
import re
import time
import PyPDF2
from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from flask_cors import CORS

# ==========================
# Load Environment Variables
# ==========================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_KEY_SECRET = os.getenv("API_KEY_SECRET")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY not found in .env file")

if not API_KEY_SECRET:
    raise ValueError("❌ API_KEY_SECRET not found in .env file")

client = OpenAI(api_key=OPENAI_API_KEY)

# ==========================
# Flask Setup
# ==========================
app = Flask(__name__)

CORS(
    app,
    resources={r"/*": {"origins": "*"}},
    allow_headers=["Content-Type", "x-api-key"],
    methods=["GET", "POST", "OPTIONS"],
)

# ==========================
# PDF Loader
# ==========================
def load_pdf_content(file_path):
    content = ""
    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content += text + "\n"
    except Exception as e:
        print("PDF Error:", e)
    return content

pdf_content = load_pdf_content("./Wheedle Technologies pdf.pdf")
print("✅ PDF Loaded")

# ==========================
# Static Company Responses
# ==========================
company_responses = {
    "website": "Visit our website: https://wheedletechnologies.ai/",
    "internship": "We offer internships in AI/ML and software development.",
    "contact": "Email: contact@wheedletechnologies.ai | Office: Sector 62, Noida",
    "about": "Wheedle Technologies is an innovative IT company specializing in AI, Cloud, and custom software solutions.",
    "projects": "We have delivered projects in healthcare, finance, and education.",
    "mission": "Our mission is to empower businesses with cutting-edge AI and cloud solutions.",
    "vision": "Our vision is to be a global leader in AI-driven digital transformation.",
    "bye": "Goodbye! Have a great day 👋",
    "thank you": "You're welcome! Happy to help 😊",
    "hello": "Hello! How can I assist you today?",
    "hi": "Hi there! What would you like to know?",
    "good morning": "Good morning! ☀️",
    "good afternoon": "Good afternoon!",
    "good evening": "Good evening!",
    "how are you": "I'm doing great, thanks for asking!"
}

# ==========================
# Guardrails
# ==========================
blocked_keywords = ["hack", "fraud", "illegal", "scam"]

blocked_patterns = [
    r"\b(fuck|shit|bitch|asshole|abuse|sex|porn)\b",
    r"ignore previous instructions",
    r"system prompt",
    r"act as",
    r"jailbreak",
    r"sql|drop table|insert into",
    r"<script>|</script>",
    r"password|otp|credit card|cvv|ssn",
    r"legal advice|medical advice|investment advice",
    r"prescription|diagnose|loan|tax advice",
    r"confirm order|refund|guarantee|discount",
    r"competitor|better than|worst company",
    r"politics|religion"
]

# ==========================
# Wheedle Topic Keywords
# ==========================
wheedle_keywords = [
    "wheedle", "services", "ai", "cloud", "software", "web", "app", "consulting",
    "marketing", "design", "career", "internship", "project", "about", "contact", "company", "it"
]

service_keywords = ["service", "services", "offer", "provide", "what do you do"]

# ==========================
# API Key Middleware
# ==========================
@app.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return "", 200

    if request.endpoint == "chat":
        api_key = request.headers.get("x-api-key")
        if api_key != API_KEY_SECRET:
            return jsonify({"reply": "Unauthorized", "success": False}), 401

# ==========================
# AI Response (Structured & Short)
# ==========================
def ai_response(user_input):
    try:
        # If the user asks about services, force structured answer
        prompt_user = user_input
        if any(word in user_input.lower() for word in service_keywords):
            prompt_user = "List all services provided by Wheedle Technologies in a structured, numbered format."

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the official AI assistant of Wheedle Technologies.\n\n"
                        "Rules:\n"
                        "- Answer ONLY about Wheedle Technologies.\n"
                        "- Keep answers SHORT (2–5 lines max).\n"
                        "- Use numbered or bullet lists for services, projects, or contact information.\n"
                        "- Bold main points and keep explanations concise.\n"
                        "- For unrelated questions, reply:\n"
                        "  'I can only assist with questions related to Wheedle Technologies.'\n\n"
                        f"Company Information:\n{pdf_content[:8000]}"
                    )
                },
                {"role": "user", "content": prompt_user}
            ],
            temperature=0.2,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print("AI Error:", e)
        return "AI service is temporarily unavailable."

# ==========================
# Chat Route
# ==========================
@app.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    data = request.get_json(silent=True) or {}
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "Please enter a message.", "success": False})

    lower_input = user_input.lower()

    # Block harmful content
    if any(word in lower_input for word in blocked_keywords):
        return jsonify({"reply": "This request is not allowed.", "success": False})

    for pattern in blocked_patterns:
        if re.search(pattern, lower_input):
            return jsonify({"reply": "I can’t help with that request.", "success": False})

    # Static quick responses
    for key, value in company_responses.items():
        if key in lower_input:
            return jsonify({"reply": value, "success": True})

    # Ensure question is Wheedle-related
    if not any(word in lower_input for word in wheedle_keywords):
        return jsonify({
            "reply": "I can only answer questions related to Wheedle Technologies and our services.",
            "success": False
        })

    # AI Structured Answer
    answer = ai_response(user_input)
    return jsonify({"reply": answer, "success": True})

# ==========================
# Run Server
# ==========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
