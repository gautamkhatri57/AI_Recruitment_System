import io
import re
from pathlib import Path

from PyPDF2 import PdfReader
from docx import Document


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_extracted_text(text: str) -> str:
    if not text:
        return ""

    # Remove null characters
    text = text.replace("\x00", " ")

    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove excessive spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


# ============================================================
# PDF
# ============================================================

def extract_text_from_pdf(file_bytes):
    """
    Extract text from normal text-based PDF.

    If the PDF has no readable text, OCR fallback is attempted.
    """

    if not file_bytes:
        raise ValueError("Uploaded PDF file is empty.")

    text = ""

    try:
        pdf_file = io.BytesIO(file_bytes)
        reader = PdfReader(pdf_file)

        for page in reader.pages:
            try:
                page_text = page.extract_text()

                if page_text:
                    text += page_text + "\n"
            except Exception:
                # Continue with other pages
                continue

    except Exception as e:
        raise ValueError(
            f"PDF reading failed: {str(e)}"
        )

    text = clean_extracted_text(text)

    # --------------------------------------------------------
    # OCR FALLBACK
    # --------------------------------------------------------

    if len(text) < 50:
        try:
            text = extract_pdf_with_ocr(file_bytes)
        except Exception:
            # Do not expose OCR library errors to user
            pass

    text = clean_extracted_text(text)

    if not text:
        raise ValueError(
            "Could not extract readable text from this PDF. "
            "The file may be password protected, corrupted, "
            "or contain only images."
        )

    return text


# ============================================================
# DOCX
# ============================================================

def extract_text_from_docx(file_bytes):
    if not file_bytes:
        raise ValueError("Uploaded DOCX file is empty.")

    text_parts = []

    try:
        docx_file = io.BytesIO(file_bytes)
        document = Document(docx_file)

        # Paragraphs
        for paragraph in document.paragraphs:
            value = paragraph.text.strip()

            if value:
                text_parts.append(value)

        # Tables
        for table in document.tables:
            for row in table.rows:
                row_values = []

                for cell in row.cells:
                    value = cell.text.strip()

                    if value:
                        row_values.append(value)

                if row_values:
                    text_parts.append(" | ".join(row_values))

    except Exception as e:
        raise ValueError(
            f"DOCX extraction failed: {str(e)}"
        )

    text = clean_extracted_text(
        "\n".join(text_parts)
    )

    if not text:
        raise ValueError(
            "Could not extract readable text from this DOCX file."
        )

    return text


# ============================================================
# DOC
# ============================================================

def extract_text_from_doc(file_bytes):
    """
    Old Microsoft Word .doc files.

    Uses antiword if installed.
    """

    if not file_bytes:
        raise ValueError("Uploaded DOC file is empty.")

    try:
        import subprocess
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(
            suffix=".doc",
            delete=False
        ) as temp_file:

            temp_file.write(file_bytes)
            temp_path = temp_file.name

        try:
            result = subprocess.run(
                ["antiword", temp_path],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                text = clean_extracted_text(result.stdout)

                if text:
                    return text

        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass

    except Exception:
        pass

    raise ValueError(
        "Could not extract text from this DOC file. "
        "Please convert it to DOCX or PDF."
    )


# ============================================================
# TXT
# ============================================================

def extract_text_from_txt(file_bytes):
    if not file_bytes:
        raise ValueError("Uploaded TXT file is empty.")

    encodings = [
        "utf-8",
        "utf-8-sig",
        "cp1252",
        "latin-1"
    ]

    for encoding in encodings:
        try:
            text = file_bytes.decode(encoding)
            text = clean_extracted_text(text)

            if text:
                return text

        except UnicodeDecodeError:
            continue

    raise ValueError(
        "Could not decode this TXT file."
    )


# ============================================================
# RTF
# ============================================================

def extract_text_from_rtf(file_bytes):
    if not file_bytes:
        raise ValueError("Uploaded RTF file is empty.")

    try:
        from striprtf.striprtf import rtf_to_text

        raw_text = file_bytes.decode(
            "utf-8",
            errors="ignore"
        )

        text = rtf_to_text(raw_text)

        text = clean_extracted_text(text)

        if text:
            return text

    except Exception:
        pass

    raise ValueError(
        "Could not extract text from this RTF file."
    )


# ============================================================
# PPTX
# ============================================================

def extract_text_from_pptx(file_bytes):
    if not file_bytes:
        raise ValueError("Uploaded PPTX file is empty.")

    try:
        from pptx import Presentation

        presentation = Presentation(
            io.BytesIO(file_bytes)
        )

        text_parts = []

        for slide in presentation.slides:
            for shape in slide.shapes:

                if hasattr(shape, "text"):
                    value = shape.text.strip()

                    if value:
                        text_parts.append(value)

        text = clean_extracted_text(
            "\n".join(text_parts)
        )

        if text:
            return text

    except Exception:
        pass

    raise ValueError(
        "Could not extract text from this PPTX file."
    )


# ============================================================
# XLSX
# ============================================================

def extract_text_from_xlsx(file_bytes):
    if not file_bytes:
        raise ValueError("Uploaded XLSX file is empty.")

    try:
        from openpyxl import load_workbook

        workbook = load_workbook(
            io.BytesIO(file_bytes),
            read_only=True,
            data_only=True
        )

        text_parts = []

        for worksheet in workbook.worksheets:

            for row in worksheet.iter_rows(
                values_only=True
            ):

                values = []

                for cell in row:
                    if cell is not None:
                        values.append(str(cell))

                if values:
                    text_parts.append(
                        " | ".join(values)
                    )

        text = clean_extracted_text(
            "\n".join(text_parts)
        )

        if text:
            return text

    except Exception:
        pass

    raise ValueError(
        "Could not extract text from this XLSX file."
    )


# ============================================================
# IMAGE OCR
# ============================================================

def extract_text_from_image(file_bytes):
    """
    OCR for JPG / JPEG / PNG / WEBP images.
    """

    if not file_bytes:
        raise ValueError("Uploaded image is empty.")

    try:
        from PIL import Image
        import pytesseract

        image = Image.open(
            io.BytesIO(file_bytes)
        )

        text = pytesseract.image_to_string(
            image
        )

        text = clean_extracted_text(text)

        if text:
            return text

    except Exception:
        pass

    raise ValueError(
        "Could not extract text from this image."
    )


# ============================================================
# PDF OCR
# ============================================================

def extract_pdf_with_ocr(file_bytes):
    """
    OCR fallback for scanned/image-based PDFs.
    """

    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        pages = convert_from_bytes(
            file_bytes,
            dpi=200
        )

        text_parts = []

        for page in pages:

            page_text = pytesseract.image_to_string(
                page
            )

            if page_text:
                text_parts.append(page_text)

        return clean_extracted_text(
            "\n".join(text_parts)
        )

    except Exception as e:
        raise ValueError(
            f"OCR failed: {str(e)}"
        )


# ============================================================
# MAIN FILE EXTRACTOR
# ============================================================

def extract_text_from_file(file_bytes, filename):

    if not file_bytes:
        raise ValueError(
            "Uploaded file is empty."
        )

    if not filename:
        raise ValueError(
            "Filename is missing."
        )

    extension = Path(
        filename
    ).suffix.lower()

    # PDF
    if extension == ".pdf":
        return extract_text_from_pdf(
            file_bytes
        )

    # Microsoft Word
    if extension == ".docx":
        return extract_text_from_docx(
            file_bytes
        )

    if extension == ".doc":
        return extract_text_from_doc(
            file_bytes
        )

    # Text
    if extension == ".txt":
        return extract_text_from_txt(
            file_bytes
        )

    # Rich Text
    if extension == ".rtf":
        return extract_text_from_rtf(
            file_bytes
        )

    # PowerPoint
    if extension == ".pptx":
        return extract_text_from_pptx(
            file_bytes
        )

    # Excel
    if extension == ".xlsx":
        return extract_text_from_xlsx(
            file_bytes
        )

    # Images
    if extension in [
        ".jpg",
        ".jpeg",
        ".png",
        ".webp"
    ]:
        return extract_text_from_image(
            file_bytes
        )

    raise ValueError(
        "Unsupported file format. "
        "Please upload a resume in PDF, DOCX, DOC, "
        "TXT, RTF, PPTX, XLSX, JPG, JPEG, PNG or WEBP format."
    )