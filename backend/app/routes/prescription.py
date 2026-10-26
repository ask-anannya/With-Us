from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlmodel import Session

from .. import settings
from ..ai import prescription as reader
from ..auth import current_member, household_of
from ..db import get_session
from ..engine.weights import WEEKDAYS
from ..models import Member, Prescription, Responsibility
from ..planning import log, replan

router = APIRouter(prefix="/api")
IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}


@router.get("/prescription/sample")
def sample_sheet():
    path = settings.SEED_DIR / "discharge-sheet.png"
    if not path.exists():
        raise HTTPException(404, "Run python -m app.seed to create the sample sheet.")
    return FileResponse(path, media_type="image/png", filename="sample-discharge-sheet.png")


@router.post("/prescription")
async def upload(file: UploadFile | None = File(None), text: str = Form(""), use_sample: bool = Form(False),
                 me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    image, mime, image_path = None, "image/png", ""
    if use_sample:
        path = settings.SEED_DIR / "discharge-sheet.png"
        if not path.exists():
            raise HTTPException(404, "The sample sheet hasn't been generated yet.")
        image, image_path = path.read_bytes(), str(path)
    elif file is not None and file.filename:
        mime = file.content_type or "image/png"
        if mime not in IMAGE_TYPES:
            raise HTTPException(400, "Please upload a PNG or JPEG photo of the sheet, or paste the text.")
        image = await file.read()
        if len(image) > 8 * 1024 * 1024:
            raise HTTPException(400, "That photo is too large. Try one under 8 MB.")
        settings.UPLOAD_DIR.mkdir(exist_ok=True)
        dest = settings.UPLOAD_DIR / f"sheet-{h.id}-{int(datetime.now().timestamp())}.{mime.split('/')[1]}"
        dest.write_bytes(image)
        image_path = str(dest)
    if image is None and not text.strip():
        raise HTTPException(400, "Upload a photo of the sheet or paste its text.")

    items = reader.read(image=image, mime_type=mime, text=text)
    used_ai = items is not None
    message = ""
    if items is None:
        items = reader.fallback_from_text(text) if text.strip() else []
        message = ("We couldn't read the sheet automatically. Check each line, or add the "
                   "instructions by hand below.")
    elif not items:
        message = "We didn't find any instructions. Add them by hand below."
    p = Prescription(household_id=h.id, image_path=image_path, text=text, extracted_json=items, used_ai=used_ai)
    s.add(p)
    s.commit()
    s.refresh(p)
    return {"id": p.id, "items": items, "used_ai": used_ai, "message": message}


class ConfirmItem(BaseModel):
    title: str
    original_line: str = ""
    schedule: str = ""
    days: list[str] = []
    time: str = ""
    icon: str = "walk"


class ConfirmBody(BaseModel):
    items: list[ConfirmItem]


@router.post("/prescription/{pid}/confirm")
def confirm(pid: int, body: ConfirmBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    h = household_of(s, me)
    p = s.get(Prescription, pid)
    if not p or p.household_id != h.id:
        raise HTTPException(404, "Sheet not found.")
    if p.confirmed_at:
        raise HTTPException(409, "This sheet was already confirmed.")
    created = 0
    for it in body.items:
        if not it.title.strip():
            continue
        start = it.time if len(it.time) == 5 and it.time[2] == ":" else None
        s.add(Responsibility(
            household_id=h.id, title=it.title.strip(), kind="recovery", work_kind="",
            days=[d for d in it.days if d in WEEKDAYS], start=start, end=None, hours_per_occurrence=0.25,
            fixed_owner_id=h.mother_member_id, source="prescription", source_line=it.original_line.strip(),
            schedule=it.schedule.strip(), icon=it.icon if it.icon in ("walk", "medicine", "wound", "visit", "rest") else "walk",
        ))
        created += 1
    p.confirmed_by = me.id
    p.confirmed_at = datetime.now()
    s.add(p)
    s.commit()
    if not replan(s, h):
        log(s, h, "Doctor's instructions confirmed")
        s.commit()
    return {"created": created}


class ManualBody(BaseModel):
    item: ConfirmItem


@router.post("/prescription/manual")
def manual(body: ManualBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    """Fallback: add one instruction by hand, same fields as the confirm screen."""
    h = household_of(s, me)
    p = Prescription(household_id=h.id, text=body.item.original_line, extracted_json=[body.item.model_dump()])
    s.add(p)
    s.commit()
    s.refresh(p)
    return confirm(p.id, ConfirmBody(items=[body.item]), me, s)
