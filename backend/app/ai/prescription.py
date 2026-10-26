"""Discharge sheet reader. Sees only the uploaded image or pasted text, never member data.
Extracts what is written; never adds, changes, explains or interprets medical advice."""
from typing import Literal

from pydantic import BaseModel

from ..engine.weights import WEEKDAYS
from .client import generate_json, image_part

SYSTEM = f"""You read a doctor's discharge sheet for a new mother and list each instruction.
Rules:
- Extract only what is written. Never add, change, explain or interpret medical advice.
- Never give doses beyond the exact written words.
- title: the instruction in short plain words, keeping every medical detail as written.
- original_line: the exact line from the sheet.
- schedule: when it happens, in plain words, as written (for example "Daily", "Friday 11 am", "Day 10").
- days: which weekdays it applies to, using {", ".join(WEEKDAYS)}. Daily means all seven. If it is a
  single future date or day number you can't map to a weekday, leave days empty.
- time: "HH:MM" 24-hour if a time is written, else "".
- icon: walk, medicine, wound, visit or rest, whichever fits best.
- unclear: true if the line is unreadable or ambiguous; then the person will be told "Ask your doctor".
Ignore headers, the patient name and footers. Return JSON only."""


class Item(BaseModel):
    title: str
    original_line: str
    schedule: str = ""
    days: list[str] = []
    time: str = ""
    icon: Literal["walk", "medicine", "wound", "visit", "rest"] = "walk"
    unclear: bool = False


class Sheet(BaseModel):
    items: list[Item]


def _clean(items: list) -> list:
    out = []
    for it in items:
        d = it.model_dump() if hasattr(it, "model_dump") else dict(it)
        d["days"] = [x for x in d.get("days", []) if x in WEEKDAYS]
        out.append(d)
    return out


def read(image: bytes | None = None, mime_type: str = "image/png", text: str = "") -> list | None:
    contents = []
    if image:
        contents.append(image_part(image, mime_type))
        contents.append("List every instruction on this discharge sheet.")
    if text.strip():
        contents.append(f"Discharge sheet text:\n{text}")
    if not contents:
        return []
    out = generate_json(SYSTEM, contents, Sheet, temperature=0.0)
    if out is None:
        return None
    return _clean(out.items)


def guess_icon(line: str) -> str:
    l = line.lower()
    if any(w in l for w in ("walk", "move", "exercise")):
        return "walk"
    if any(w in l for w in ("tablet", "pill", "capsule", "medicine", "syrup", "iron")):
        return "medicine"
    if any(w in l for w in ("wound", "stitch", "dressing", "incision")):
        return "wound"
    if any(w in l for w in ("follow", "visit", "appointment", "review", "check-up")):
        return "visit"
    return "rest"


def fallback_from_text(text: str) -> list:
    """No AI: each non-empty pasted line becomes a row for a person to confirm."""
    rows = []
    for line in text.splitlines():
        line = line.strip().lstrip("-*0123456789.) \t").strip()
        if len(line) < 3:
            continue
        daily = "daily" in line.lower() or "every day" in line.lower()
        rows.append({"title": line, "original_line": line, "schedule": "Daily" if daily else "",
                     "days": list(WEEKDAYS) if daily else [], "time": "", "icon": guess_icon(line),
                     "unclear": not daily})
    return rows
