"""
Automated unit test suite for SIH26237 Forensic Watermarking Engine.
Tests token generation, non-rendering embedding, extraction, visual invariance, and uniqueness.
"""

import sys
import os
import shutil
from pathlib import Path
import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testenv  # noqa: E402,F401

from app.watermark.embed import generate_watermark_token, embed_watermark
from app.watermark.extract import extract_watermark
from app.watermark.validate import validate_visual_invariance

def create_sample_pdf() -> bytes:
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 80), "INDIAN NAVY - WESEE DEFENCE DIRECTIVE", fontsize=16, color=(0, 0, 0.5))
    page.insert_text((50, 110), "DOCUMENT CLASSIFICATION: CONFIDENTIAL", fontsize=11, color=(0.8, 0, 0))
    page.insert_text((50, 150), "Operational Brief: Fleet Deployment Order 2026-ALPHA.", fontsize=12)
    page.insert_text((50, 175), "Vessels Assigned: INS Vikrant, INS Kolkata, INS Chennai.", fontsize=11)
    page.insert_text((50, 200), "All decrypting stations must log local post-quantum cryptographic proof.", fontsize=11)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_watermark_lifecycle():
    print("Testing Watermark Generation, Non-Rendering Embedding, and Extraction...")
    original_pdf = create_sample_pdf()
    
    # 1. Generate opaque token
    wm_token = generate_watermark_token()
    assert wm_token.startswith("WM-"), "Token does not have expected prefix"
    assert len(wm_token) == 67, f"Unexpected token length: {len(wm_token)}"
    
    # 2. Embed into PDF
    watermarked_pdf = embed_watermark(original_pdf, wm_token)
    assert len(watermarked_pdf) > len(original_pdf), "Watermarked PDF bytes smaller than original"
    
    # 3. Extract from PDF
    extracted_token = extract_watermark(watermarked_pdf)
    assert extracted_token == wm_token, f"Extraction failed! Expected {wm_token}, got {extracted_token}"
    print("[OK] Watermark Lifecycle (Generate -> Embed -> Extract) Passed.")

def test_visual_invariance():
    print("Testing Visual Pixel Invariance (Original vs Watermarked)...")
    original_pdf = create_sample_pdf()
    wm_token = generate_watermark_token()
    watermarked_pdf = embed_watermark(original_pdf, wm_token)
    
    result = validate_visual_invariance(original_pdf, watermarked_pdf)
    assert result["is_visually_identical"] is True, f"Visual deviation detected: {result}"
    assert result["differing_pixels"] == 0, f"Non-zero differing pixels: {result['differing_pixels']}"
    print(f"[OK] Visual Invariance Verified (0 pixel diff out of {result['total_pixels_compared']} pixels).")

def test_watermark_uniqueness_across_sessions():
    print("Testing Multi-Recipient / Multi-Session Watermark Uniqueness...")
    original_pdf = create_sample_pdf()
    
    tokens = set()
    for i in range(5):
        token = generate_watermark_token()
        assert token not in tokens, "Duplicate watermark token generated!"
        tokens.add(token)
        wm_pdf = embed_watermark(original_pdf, token)
        extracted = extract_watermark(wm_pdf)
        assert extracted == token, "Mismatched token extraction during uniqueness test"
    assert len(tokens) == 5
    print("[OK] Session Watermark Uniqueness Test Passed.")

def test_file_operations_resilience():
    print("Testing File Operations Resilience (Save, Copy, Rename)...")
    original_pdf = create_sample_pdf()
    token = generate_watermark_token()
    wm_pdf = embed_watermark(original_pdf, token)
    
    temp_dir = Path(__file__).resolve().parent / "temp_test"
    temp_dir.mkdir(exist_ok=True)
    
    try:
        # File 1: Save
        file1 = temp_dir / "decrypted_doc.pdf"
        file1.write_bytes(wm_pdf)
        
        # File 2: Copy
        file2 = temp_dir / "copied_doc.pdf"
        shutil.copyfile(file1, file2)
        
        # File 3: Rename
        file3 = temp_dir / "LEAKED_SUSPECT_DOCUMENT.pdf"
        shutil.move(file2, file3)
        
        # Extract from renamed file
        extracted = extract_watermark(file3.read_bytes())
        assert extracted == token, f"Extraction failed after file operations! Got: {extracted}"
        print("[OK] File Operations Resilience (Save -> Copy -> Rename) Passed.")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    test_watermark_lifecycle()
    test_visual_invariance()
    test_watermark_uniqueness_across_sessions()
    test_file_operations_resilience()
    print("\nALL WATERMARK TESTS PASSED.")
