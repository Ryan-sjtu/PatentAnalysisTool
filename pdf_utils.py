import fitz  # PyMuPDF

# （从PDF提取文本）

def extract_pdf_text(pdf_bytes: bytes, max_pages: int = 200) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    n_pages = min(len(doc), max_pages)

    parts = []
    for i in range(n_pages):
        page = doc[i]
        txt = page.get_text("text")
        if txt:
            parts.append(f"\n\n===== Page {i+1} =====\n{txt}")

    doc.close()
    return "\n".join(parts).strip()
