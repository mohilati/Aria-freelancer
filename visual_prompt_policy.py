"""
Visual Prompt Policy for premium skincare/dermatology ads.

This is a deterministic prompt builder: it makes every scene explicit about
clinical realism, human anatomy, continuity, camera language and exclusions.
It is designed to reduce generic/warped AI imagery.
"""

from __future__ import annotations

from typing import Any, Dict, List

BASE_NEGATIVE = [
    "deformed hands",
    "extra fingers",
    "missing fingers",
    "duplicate person",
    "asymmetrical eyes",
    "warped face",
    "plastic skin",
    "wax skin",
    "over-smoothed skin",
    "unrealistic pores",
    "fake medical equipment",
    "fantasy clinic",
    "empty eyes",
    "bad teeth",
    "text inside image",
    "random logo",
    "watermark",
    "oversaturated beauty ad",
    "extreme beauty filter",
]

def build_clinic_scene_prompt(
    scene: Dict[str, Any],
    continuity: Dict[str, Any],
    real_reference_note: str = "",
) -> str:
    """Build an English generation prompt for a realistic Persian clinic ad."""
    subject = scene.get("subject") or "adult Persian-speaking skincare client"
    action = scene.get("action") or "speaking naturally with a calm expression"
    location = scene.get("location") or "modern professional dermatology clinic"
    shot = scene.get("shot") or "medium cinematic shot"
    lighting = scene.get("lighting") or "soft neutral clinical lighting"
    wardrobe = scene.get("wardrobe") or "simple elegant neutral clothing"
    mood = scene.get("mood") or "trustworthy, calm, premium"

    continuity_text = ""
    if continuity:
        continuity_text = (
            f"Keep the same main client across scenes: {continuity.get('appearance','same adult client')}. "
            f"Keep consistent hair, face shape, skin tone, wardrobe and age. "
        )

    reference = f"Use the supplied real clinic reference as the visual source of truth. {real_reference_note} " if real_reference_note else ""

    negatives = ", ".join(BASE_NEGATIVE)

    return (
        "Photorealistic premium dermatology clinic advertisement, documentary-commercial realism. "
        f"{reference}"
        f"{continuity_text}"
        f"Subject: {subject}. "
        f"Action: {action}. "
        f"Location: {location}. "
        f"Composition: {shot}. "
        f"Lighting: {lighting}. "
        f"Wardrobe: {wardrobe}. "
        f"Emotion and mood: {mood}. "
        "Natural human proportions, believable Persian/Middle Eastern features, realistic skin texture, "
        "subtle pores and natural imperfections, physically plausible hands, authentic clinical materials, "
        "professional but not luxurious fantasy styling, shallow depth of field, realistic lens behavior, "
        "cinematic but restrained color grading, vertical 9:16 composition, subject centered safely for subtitles. "
        f"Do not include: {negatives}."
    )

def scene_bible(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "main_client": (
            "adult Persian/Middle Eastern client, natural facial proportions, "
            "healthy realistic skin texture, consistent hairstyle and neutral wardrobe"
        ),
        "clinic": "realistic dermatology/skin clinic, clean and professional",
        "format": "9:16 vertical",
        "reference_required": bool(job.get("reference_images")),
    }
