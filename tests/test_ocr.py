import pytest
from PIL import Image, ImageDraw, ImageFont
import io
from app.pipeline.ocr import extract_text_from_image


def test_ocr_with_text_image():
    # Create an in-memory image with clear English text
    img = Image.new("RGB", (500, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Draw simple text
    draw.text((20, 40), "URGENT NOTICE CBI OFFICER", fill=(0, 0, 0))

    resp = extract_text_from_image(img)
    assert resp.success is True
    assert "CBI" in resp.extracted_text.upper() or "URGENT" in resp.extracted_text.upper()


def test_ocr_with_blank_image():
    # Completely blank white image
    img = Image.new("RGB", (300, 100), color=(255, 255, 255))
    resp = extract_text_from_image(img)
    assert resp.success is False
    assert "No text found" in resp.message


def test_ocr_with_invalid_bytes():
    resp = extract_text_from_image(b"not an image file")
    assert resp.success is False
    assert "Could not read text from image" in resp.message
