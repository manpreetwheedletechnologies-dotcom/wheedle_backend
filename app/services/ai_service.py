from .pdf_service import load_pdf_content
from app.config import client

pdf_content = load_pdf_content("./Wheedle Technologies pdf.pdf")

def generate_ai_response(user_input):

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"""
You are the official AI assistant of Wheedle Technologies.

Rules:
- Answer ONLY about Wheedle Technologies.
- Keep answers SHORT (2–5 lines max).

Company Information:
{pdf_content[:8000]}
"""
            },
            {"role": "user", "content": user_input}
        ],
        temperature=0.2,
        max_tokens=150
    )

    return response.choices[0].message.content.strip()
