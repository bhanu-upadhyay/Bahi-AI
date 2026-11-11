import io
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
import fitz  # PyMuPDF
from PIL import Image, ImageOps, ImageEnhance
import pytesseract

logger = logging.getLogger("bahi_ai.ocr")


class OCRExtractionError(Exception):
    """Raised when document reading or OCR completely fails."""
    pass


def preprocess_image_for_ocr(image: Image.Image) -> Image.Image:
    """Preprocesses a PIL Image for improved OCR recognition.
    - Transposes EXIF orientation if present.
    - Converts to grayscale.
    - Enhances contrast slightly.
    """
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    # Convert to grayscale
    gray = image.convert("L")

    # Enhance contrast
    try:
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(1.5)
        return enhanced
    except Exception:
        return gray


def extract_text_from_pdf(pdf_path: Path) -> Tuple[str, str, Dict[str, Any]]:
    """Extracts text from PDF:
    1. Tests whether PDF contains digital text layer.
    2. Falls back to page-by-page OCR rendering if digital text is absent or sparse.
    """
    metadata: Dict[str, Any] = {"page_count": 0, "pages": []}
    text_blocks = []

    try:
        doc = fitz.open(str(pdf_path))
        metadata["page_count"] = len(doc)
    except Exception as e:
        logger.error(f"Failed to open PDF document at {pdf_path}: {e}")
        raise OCRExtractionError(f"Could not open or parse PDF document: {e}")

    # Pass 1: Check digital text layer
    digital_text_by_page = []
    total_digital_chars = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        p_text = page.get_text() or ""
        clean_p = p_text.strip()
        digital_text_by_page.append(clean_p)
        total_digital_chars += len("".join(clean_p.split()))

    # If digital text exists with sufficient density (> 60 alphanumeric/word chars)
    if total_digital_chars >= 60:
        logger.info(f"PDF {pdf_path.name} contains digital text layer ({total_digital_chars} chars). Using PyMuPDF.")
        combined_text = "\n\n".join(digital_text_by_page)
        metadata["ocr_method"] = "PYMUPDF_DIGITAL"
        metadata["character_count"] = len(combined_text)
        return combined_text, "PYMUPDF_DIGITAL", metadata

    # Pass 2: Scanned PDF fallback to Tesseract OCR
    logger.info(f"PDF {pdf_path.name} has sparse digital text ({total_digital_chars} chars). Running Tesseract OCR.")
    ocr_pages_text = []

    for page_num in range(len(doc)):
        try:
            page = doc[page_num]
            # Render page to high-res pixmap (300 DPI for high fidelity)
            pix = page.get_pixmap(dpi=300)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            processed_img = preprocess_image_for_ocr(img)

            page_ocr_text = pytesseract.image_to_string(processed_img)
            ocr_pages_text.append(page_ocr_text.strip())
            metadata["pages"].append({
                "page": page_num + 1,
                "width": pix.width,
                "height": pix.height,
                "text_length": len(page_ocr_text),
            })
        except Exception as e:
            logger.warning(f"Error OCR-ing page {page_num} of {pdf_path.name}: {e}")
            ocr_pages_text.append("")

    combined_text = "\n\n".join(ocr_pages_text).strip()
    # If both digital and OCR yielded some text, combine
    if total_digital_chars > 0 and len(combined_text) < total_digital_chars:
        combined_text = "\n\n".join(digital_text_by_page).strip()
        method = "HYBRID"
    else:
        method = "TESSERACT_OCR"

    metadata["ocr_method"] = method
    metadata["character_count"] = len(combined_text)
    return combined_text, method, metadata


def extract_text_from_image(image_path: Path) -> Tuple[str, str, Dict[str, Any]]:
    """Extracts text from PNG or JPEG image using Pillow preprocessing and Tesseract OCR."""
    metadata: Dict[str, Any] = {}
    try:
        img = Image.open(image_path)
        metadata["format"] = img.format
        metadata["size"] = img.size

        processed_img = preprocess_image_for_ocr(img)
        text = pytesseract.image_to_string(processed_img)
        clean_text = text.strip()

        metadata["ocr_method"] = "TESSERACT_OCR"
        metadata["character_count"] = len(clean_text)
        return clean_text, "TESSERACT_OCR", metadata
    except Exception as e:
        logger.error(f"Image OCR failed for {image_path}: {e}")
        raise OCRExtractionError(f"Failed to process image through OCR: {e}")


def extract_document_text(file_path: Path, mime_type: str) -> Tuple[str, str, Dict[str, Any]]:
    """Dispatches document to PDF text extractor or image OCR based on MIME type."""
    if mime_type == "application/pdf":
        return extract_text_from_pdf(file_path)
    elif mime_type in ["image/png", "image/jpeg", "image/jpg"]:
        return extract_text_from_image(file_path)
    else:
        raise OCRExtractionError(f"Unsupported MIME type for OCR: {mime_type}")
