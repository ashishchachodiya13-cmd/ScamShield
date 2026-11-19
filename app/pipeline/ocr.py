import os
import io
from pathlib import Path
from typing import Union, BinaryIO
from PIL import Image
import pytesseract
from dotenv import load_dotenv

from app.schemas import OCRResponse

load_dotenv()


def _configure_tesseract():
    """Sets up tesseract executable path and project-level tessdata prefix."""
    # 1. Configure tesseract binary path
    env_path = os.getenv("TESSERACT_PATH")
    if env_path and os.path.exists(env_path):
        pytesseract.pytesseract.tesseract_cmd = env_path
    else:
        # Common Windows standard location
        default_win_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.path.exists(default_win_path):
            pytesseract.pytesseract.tesseract_cmd = default_win_path

    # 2. Set TESSDATA_PREFIX to our local project tessdata if available
    project_tessdata = Path(__file__).resolve().parent.parent.parent / "data" / "tessdata"
    if project_tessdata.exists() and (project_tessdata / "eng.traineddata").exists():
        os.environ["TESSDATA_PREFIX"] = str(project_tessdata)


# Initialize configuration
_configure_tesseract()


def extract_text_from_image(image_input: Union[str, Path, bytes, BinaryIO, Image.Image]) -> OCRResponse:
    """
    Extracts text from an uploaded screenshot using Tesseract OCR (eng + hin).
    Supports reviewing and correcting the extracted text before downstream analysis (UC4, UC5).
    """
    try:
        # Handle input types
        if isinstance(image_input, Image.Image):
            img = image_input
        elif isinstance(image_input, (str, Path)):
            img = Image.open(image_input)
        elif isinstance(image_input, bytes):
            img = Image.open(io.BytesIO(image_input))
        else:
            img = Image.open(image_input)

        # Image preprocessing to optimize OCR quality
        # Convert RGBA to RGB with white background if transparent
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[3])
            img = background
        else:
            img = img.convert("RGB")

        # Languages: English + Hindi
        langs = "eng+hin"

        # Perform OCR
        extracted = pytesseract.image_to_string(img, lang=langs)
        cleaned_text = extracted.strip()

        if not cleaned_text:
            return OCRResponse(
                extracted_text="",
                success=False,
                message="No text found in the image. Please upload a clearer screenshot or paste the text directly."
            )

        return OCRResponse(
            extracted_text=cleaned_text,
            success=True,
            message="Text successfully extracted. Please review and correct any words below before analyzing."
        )

    except pytesseract.TesseractNotFoundError:
        return OCRResponse(
            extracted_text="",
            success=False,
            message="Tesseract OCR engine is not configured. Please paste your message text directly."
        )
    except Exception as e:
        return OCRResponse(
            extracted_text="",
            success=False,
            message=f"Could not read text from image: {str(e)}. Please paste your message text directly."
        )
