import os
import re
import time
from datetime import datetime
from flask import Blueprint, request, jsonify
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from app.config import API_KEY_SECRET, MONGO_URI, client
from app.services.guardrails_service import is_blocked
from app.services.ai_service import generate_ai_response
from app.db import mongo  # ✅ shared Flask-PyMongo (same DB as live_chat_routes)

chat_bp = Blueprint("chat", __name__)

# ==========================
# Dictionary Data
# ==========================
GREETING_WORDS = {
    "hi": "Hi Welcome to Wheedle Technologies! How can I help you today?",
    "hello": "Hello Great to see you! How may I assist you?",
    "hey": "Hey there How can I support you today?",
    "how are you": "I'm doing great! How can I assist you today?",
    "good morning": "Good Morning How can I help you today?",
    "good afternoon": "Good Afternoon How may I assist you?",
    "good evening": "Good Evening How can I support you today?",
    "bye": "Goodbye Have a wonderful day!"
}

CONTACT_DETAILS = {
    "phone": "📞 Phone: +91 9717672561",
    "email": "📧 Email: info@wheedletechnologies.ai",
    "address": "📍 Address: Sector 62, ITHM Tower, Tower C, Office No. 410",
    "full_contact": """📞 Phone: +91 9717672561
📧 Email: info@wheedletechnologies.ai
📍 Address: Sector 62, ITHM Tower, Tower C, Office No. 410"""
}

ABOUT_INFORMATION = """
Wheedle Technologies is an AI-powered technology company
specializing in autonomous digital solutions, AI engineering agents,
and scalable software platforms.
"""

# ==========================
# Website URL & Services
# ==========================
WEBSITE_URL = "https://wheedletechnologies.ai/"
CAREER_URL = "https://wheedletechnologies.ai/career"
ABOUT_URL = "https://wheedletechnologies.ai/about"
BLOG_URL = "https://wheedletechnologies.ai/blog"

SERVICES = [
    {"name": "AI Web Engineering Agents", "url": "https://wheedletechnologies.ai/service/ai-web-engineering-agents"},
    {"name": "Software Development Agentic Platform", "url": "https://wheedletechnologies.ai/service/software-development-agentic-platform"},
    {"name": "Autonomous Digital Marketing Agents", "url": "https://wheedletechnologies.ai/service/autonomous-digital-marketing-agents"},
    {"name": "Autonomous UI/UX Design", "url": "https://wheedletechnologies.ai/service/autonomous-ui/ux-design-intelligence"},
    {"name": "AI App Development Agent", "url": "https://wheedletechnologies.ai/service/ai-app-development-agent"},
    {"name": "Autonomous IT Consulting & Advisory Agent", "url": "https://wheedletechnologies.ai/service/autonomous-it-consulting-and-advisory-agent"},
    {"name": "AI Graphic Design Automation Agent", "url": "https://wheedletechnologies.ai/service/ai-graphic-design-automation-agent"},
    {"name": "AI Solutions & Intelligent Automation", "url": "https://wheedletechnologies.ai/service/ai-solutions-and-intelligent-automation"}
]

# ==========================
# Clean Content Extractor
# ==========================
def extract_clean_content(soup):
    content = []
    for tag in soup.find_all(['h1','h2','h3','p','li']):
        text = tag.get_text(strip=True)
        if text and len(text) > 40:
            content.append(text)
    return "\n".join(content)

# ==========================
# SCRAPE SERVICE DETAILS
# ==========================
def scrape_service_details(url):
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        driver.get(url)
        time.sleep(4)  # wait for JS content

        soup = BeautifulSoup(driver.page_source, "html.parser")
        content = []

        for tag in soup.find_all(["h1", "h2", "h3", "p", "li"]):
            text = tag.get_text(strip=True)
            if text and len(text) > 20:
                content.append(text)

        driver.quit()

        if not content:
            return "Content not found. Please check the service page."

        return "\n".join(content[:6])

    except Exception as e:
        return f"Error: {str(e)}"

# ==========================
# SERVICE KEYWORD MATCHER
# ==========================
def match_service(user_message):
    user_message = user_message.lower()
    words = re.findall(r'\w+', user_message)

    for service in SERVICES:
        name = service["name"].lower()
        for word in words:
            if name in user_message or any(w in user_message for w in name.split()):
                details = scrape_service_details(service["url"])
                return f"Service: {service['name']}\n\nOverview:\n{details[:500]}...\n\nLearn More:\n{service['url']}"
    return None

# ==========================
# URL MATCHER
# ==========================
def match_service_url(user_message):
    url_pattern = r'https?://[^\s]+'
    urls = re.findall(url_pattern, user_message)

    for url in urls:
        for service in SERVICES:
            if service["url"] in url:
                details = scrape_service_details(service["url"])
                return f"Service: {service['name']}\n\nOverview:\n{details[:500]}...\n\nLearn More:\n{service['url']}"
    return None

# ==========================
# Scrape Website Data
# ==========================
def scrape_full_website():
    context_data = {
        "home": "",
        "services": {},
        "career": "",
        "blog": "",
        "about": ""
    }

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(service=Service(), options=chrome_options)
    except Exception:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

    try:
        def scrape_page(url, wait=6):
            driver.get(url)
            time.sleep(wait)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            return extract_clean_content(soup)

        context_data["home"] = scrape_page(WEBSITE_URL)[:6000]
        context_data["about"] = scrape_page(ABOUT_URL)[:5000]
        context_data["career"] = scrape_page(CAREER_URL)[:5000]
        context_data["blog"] = scrape_page(BLOG_URL)[:5000]

        for service in SERVICES:
            driver.get(service["url"])
            time.sleep(4)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            context_data["services"][service["name"]] = extract_clean_content(soup)[:8000]

    finally:
        driver.quit()

    return context_data

try:
    website_data_store = scrape_full_website()
except Exception:
    website_data_store = {"home": "", "services": {}, "career": "", "blog": "", "about": ""}

# ==========================
# Career Scraper
# ==========================
def scrape_career_page():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(service=Service(), options=chrome_options)
    except Exception:
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

    jobs = []
    try:
        driver.get(CAREER_URL)
        time.sleep(5)
        soup = BeautifulSoup(driver.page_source, "html.parser")

        job_cards = soup.find_all("div", class_=lambda x: x and "rounded-[30px]" in x)

        for job in job_cards:
            title_tag = job.find("h3")
            type_tag = job.find("span")
            desc_tag = job.find("p")

            if title_tag:
               title = title_tag.get_text(strip=True)
               job_type = type_tag.get_text(strip=True) if type_tag else "N/A"
               description = desc_tag.get_text(strip=True) if desc_tag else ""
               jobs.append(f"{title} ({job_type})\n{description}")
    except Exception as e:
        return f"Error: {str(e)}"
    finally:
        driver.quit()
        if not jobs:
            return "Currently, there are no open positions listed."

    formatted_jobs = "\n\n".join([f"• {job}" for job in jobs])
    return f"Open Hiring Positions:\n\n{formatted_jobs}"


# ==========================
# Question Limit System
# ==========================
user_question_count = {}
waiting_for_contact = {}
MAX_QUESTIONS = 4

# ==========================
# Middleware - API Key Check
# ==========================
@chat_bp.before_request
def check_api_key():
    if request.method == "OPTIONS":
        return "", 200

    api_key = request.headers.get("x-api-key")
    if api_key != API_KEY_SECRET:
        return jsonify({"reply": "Unauthorized", "success": False}), 401

# ==========================
# Chatbot Route
# ==========================
@chat_bp.route("/chat", methods=["POST", "OPTIONS"])
def chat():
    if request.method == "OPTIONS":
        return jsonify({}), 200

    data = request.get_json(force=True, silent=True) or {}
    user_msg = data.get("message", "").strip()
    user_ip = request.remote_addr

    if user_ip not in user_question_count:
        user_question_count[user_ip] = 0

    if not user_msg:
        return jsonify({"reply": "Please enter a message.", "success": False})

    # Guardrails check (optional safety layer from existing codebase)
    if is_blocked(user_msg):
        return jsonify({"reply": "This request is not allowed.", "success": False})

    # If waiting for contact details
    if waiting_for_contact.get(user_ip):
        parts = user_msg.split()
        if len(parts) >= 2:
            email = parts[0]
            phone = parts[1]

            try:
                mongo.db.user_contacts.insert_one({
                    "email": email,
                    "phone": phone,
                    "ip": user_ip,
                    "created_at": datetime.utcnow()
                })
            except Exception as db_err:
                print(f"[chat] contacts DB error: {db_err}")

            waiting_for_contact[user_ip] = False

            return jsonify({
                "reply": "Thank you! Your contact details have been saved. Our team will contact you soon.",
                "success": True
            })

        return jsonify({
            "reply": "Please send Email and Phone Number like:\nexample@email.com 9876543210",
            "success": True
        })

    if user_question_count[user_ip] >= MAX_QUESTIONS:
        waiting_for_contact[user_ip] = True
        return jsonify({
            "reply": "To assist you further, please share your Email ID and Phone Number. Our team will get in touch with you shortly."
        })

    user_msg_lower = user_msg.lower()

    # Show All Services (without URL)
    if "services" in user_msg_lower or "service" in user_msg_lower:
        service_list = "Here are the services offered by Wheedle Technologies:\n\n"
        for s in SERVICES:
            service_list += f"• {s['name']}\n"
        return jsonify({"reply": service_list, "success": True})

    if user_msg_lower in GREETING_WORDS:
        response = GREETING_WORDS[user_msg_lower]
        user_question_count[user_ip] += 1
        return jsonify({"reply": response, "success": True})

    if "contact" in user_msg_lower:
        user_question_count[user_ip] += 1
        return jsonify({"reply": CONTACT_DETAILS["full_contact"], "success": True})

    # Career Page (Only Career)
    if "career" in user_msg_lower:
       return jsonify({
        "reply": f"Wheedle Technologies Career Page\n\nExplore career opportunities here:\n{CAREER_URL}",
        "success": True
    })

    # URL Service Match
    url_match = match_service_url(user_msg)
    if url_match:
        return jsonify({"reply": url_match, "success": True})

    # Word Service Match
    service_match = match_service(user_msg)
    if service_match:
        return jsonify({"reply": service_match, "success": True})

    # Restricted AI Response using ai_service
    try:
        ai_reply = generate_ai_response(user_msg)
        user_question_count[user_ip] += 1
        return jsonify({"reply": ai_reply, "success": True})

    except Exception as e:
        return jsonify({"reply": f"Sorry, I encountered an error: {str(e)}", "success": False})
