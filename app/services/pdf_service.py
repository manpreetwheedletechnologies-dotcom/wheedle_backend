import PyPDF2

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
