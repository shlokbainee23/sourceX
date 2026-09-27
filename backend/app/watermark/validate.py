"""
Visual Invariance Validator for SIH26237.
Renders both PDFs at 150 DPI and counts differing pixel channel values.
Differing page counts or page dimensions are reported as non-identical.
"""

import pymupdf
from typing import Dict, Any


def validate_visual_invariance(original_pdf_bytes: bytes, watermarked_pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Returns:
        {
            "is_visually_identical": bool,
            "total_pixels_compared": int,   # channel samples compared
            "differing_pixels": int,        # channel samples that differ
            "max_channel_deviation": int,
            "pages_verified": int,
            "page_count_match": bool,
        }
    """
    orig_doc = pymupdf.open(stream=original_pdf_bytes, filetype="pdf")
    wm_doc = pymupdf.open(stream=watermarked_pdf_bytes, filetype="pdf")

    differing = 0
    total = 0
    max_dev = 0
    page_count_match = len(orig_doc) == len(wm_doc)
    pages_count = min(len(orig_doc), len(wm_doc))
    size_mismatch = False

    try:
        for i in range(pages_count):
            pix1 = orig_doc[i].get_pixmap(dpi=150)
            pix2 = wm_doc[i].get_pixmap(dpi=150)
            s1, s2 = pix1.samples, pix2.samples
            if (pix1.width, pix1.height, pix1.n) != (pix2.width, pix2.height, pix2.n):
                size_mismatch = True
                continue
            total += len(s1)
            if s1 == s2:
                continue
            for b1, b2 in zip(s1, s2):
                if b1 != b2:
                    differing += 1
                    max_dev = max(max_dev, abs(b1 - b2))
    finally:
        orig_doc.close()
        wm_doc.close()

    return {
        "is_visually_identical": differing == 0 and page_count_match and not size_mismatch and pages_count > 0,
        "total_pixels_compared": total,
        "differing_pixels": differing,
        "max_channel_deviation": max_dev,
        "pages_verified": pages_count,
        "page_count_match": page_count_match,
    }
