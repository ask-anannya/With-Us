"""Seed the demo household (code `meera`) and the sample discharge sheet.

Run: python -m app.seed
"""
import secrets
from datetime import date, timedelta

from sqlmodel import Session, select

from . import settings
from .db import engine, init_db
from .engine.weights import WEEKDAYS
from .models import (AssistantInstructions, Household, Limit, Member, MotherSharing, PrivateReason,
                     Proposal, Responsibility, RestWindow)
from .planning import replan

ALL = WEEKDAYS
WEEKNIGHTS = ["Mon", "Tue", "Wed", "Thu", "Fri"]

KARAN_REASON = ("Client meetings every Thursday and Friday. I'm exhausted after and haven't "
                "found the words to tell Meera.")
SUNITA_REASON = "I'm a very light sleeper and can't get back to sleep."
MEERA_INSTRUCTIONS = "I never say no. When it's too much, say it for me, kindly."

# title, kind, work_kind, days, start, end, hours, travel, cold_only, preset owner
# Hours are tuned so the baseline fits and the `cold` variant leaves about 3 hours.
FIXED_OWNERS = {"Baby's doctor visits": "ramesh"}  # the whole bundle: remember, book, go
RESPONSIBILITIES = [
    ("Weeknight support", "baby", "Nights", WEEKNIGHTS, "22:00", "06:00", 1.0, False, False, "ramesh"),
    ("Weekend nights", "baby", "Nights", ["Sat", "Sun"], "22:00", "06:00", 1.0, False, False, "karan"),
    ("Baby's doctor visits", "baby", "Appointments", ["Wed"], "10:00", "12:00", 2.0, True, False, None),
    ("Go with Meera to her follow-up", "baby", "Driving", ["Fri"], "11:00", "12:30", 1.5, True, False, "sunita"),
    ("Cooking", "home", "Cooking", ALL, "08:00", "08:45", 0.75, False, False, None),
    ("Laundry", "home", "Cleaning", ["Mon", "Wed", "Sat"], None, None, 1.0, False, False, "sunita"),
    ("Groceries", "home", "Errands", ["Sat"], "10:00", "11:30", 1.5, True, False, "karan"),
    ("Baby bath", "baby", "Baby care", ALL, "18:00", "18:30", 0.5, False, False, "sunita"),
    ("Extra night feeds", "baby", "Nights", WEEKNIGHTS, "02:00", "03:00", 1.0, False, True, None),
    ("Pediatric visit for the cold", "baby", "Appointments", ["Thu"], "14:00", "17:00", 3.0, True, True, None),
]

SHEET_LINES = [
    "Walk 10 minutes daily",
    "Iron tablet after breakfast",
    "Wound check on day 10",
    "Follow-up Friday 11 am",
]


def this_monday() -> str:
    today = date.today()
    return (today - timedelta(days=today.weekday())).isoformat()


def opaque() -> str:
    return "lim_" + secrets.token_hex(4)


def make_discharge_sheet() -> None:
    """A legible, realistic-looking sample discharge summary (A4 at 150 dpi).
    The clinic, doctor and numbers are fictional; the footer marks it as a demo."""
    from PIL import Image, ImageDraw, ImageFont

    settings.SEED_DIR.mkdir(parents=True, exist_ok=True)
    W, H = 1240, 1754
    img = Image.new("RGB", (W, H), "#FFFFFF")
    d = ImageDraw.Draw(img)

    def font(size, *names):
        for name in (*names, "arial.ttf", "DejaVuSans.ttf", "Helvetica.ttc"):
            try:
                return ImageFont.truetype(name, size)
            except OSError:
                continue
        return ImageFont.load_default()

    teal, teal_dark, ink, muted, line, soft = "#2E6E73", "#1F4F53", "#1F2328", "#5B6470", "#D5DEE2", "#F2F7F7"
    regular = lambda n: font(n, "segoeui.ttf", "arial.ttf")  # noqa: E731
    bold = lambda n: font(n, "segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf")  # noqa: E731
    M = 80

    # Letterhead band with a simple lotus mark
    d.rectangle((0, 0, W, 190), fill=teal)
    d.rectangle((0, 190, W, 198), fill="#E8B4A0")
    cx, cy = M + 52, 95
    d.ellipse((cx - 52, cy - 52, cx + 52, cy + 52), fill="#FFFFFF")
    for dx, h in ((-22, 30), (22, 30), (0, 40)):
        d.ellipse((cx + dx - 13, cy - h, cx + dx + 13, cy + 18), fill="#E8A0A8" if dx else "#D9707F")
    d.rectangle((cx - 30, cy + 16, cx + 30, cy + 22), fill=teal)
    d.text((M + 130, 50), "Lotus Women & Child Clinic", fill="#FFFFFF", font=bold(46))
    d.text((M + 132, 112), "Maternity and newborn care", fill="#D8ECEC", font=regular(26))
    for i, t in enumerate(["14 Garden Lane, Sample City", "Phone: +91 00000 00000", "care@lotus-clinic.example"]):
        tw = d.textlength(t, font=regular(22))
        d.text((W - M - tw, 52 + i * 34), t, fill="#D8ECEC", font=regular(22))

    # Title
    y = 250
    d.text((M, y), "Discharge Summary", fill=ink, font=bold(44))
    d.text((M, y + 60), "Home care instructions after delivery", fill=muted, font=regular(28))
    ref = "Ref. LWC-2026-0417"
    d.text((W - M - d.textlength(ref, font=regular(22)), y + 18), ref, fill=muted, font=regular(22))

    # Patient details box
    y = 380
    d.rounded_rectangle((M, y, W - M, y + 230), radius=18, fill=soft, outline=line, width=2)
    fields = [("Patient", "Meera"), ("Procedure", "Caesarean delivery"),
              ("Baby", "Girl, healthy"), ("Ward", "Maternity, Room 12"),
              ("Treating doctor", "Dr. A. Rao, Obstetrics"), ("Discharged", "In good condition")]
    col_w = (W - 2 * M) // 2
    for i, (k, v) in enumerate(fields):
        fx = M + 36 + (i % 2) * col_w
        fy = y + 30 + (i // 2) * 64
        d.text((fx, fy), k.upper(), fill=muted, font=bold(18))
        d.text((fx, fy + 24), v, fill=ink, font=regular(28))

    # Instructions table
    y = 660
    d.text((M, y), "Instructions at home", fill=teal_dark, font=bold(34))
    d.rectangle((M, y + 52, M + 120, y + 57), fill="#E8B4A0")
    y += 90
    row_h = 104
    for i, text in enumerate(SHEET_LINES, 1):
        top = y + (i - 1) * row_h
        d.rounded_rectangle((M, top, W - M, top + row_h - 14), radius=14,
                            fill="#FFFFFF" if i % 2 else soft, outline=line, width=2)
        bx, by = M + 30, top + (row_h - 14) // 2
        d.ellipse((bx, by - 24, bx + 48, by + 24), fill=teal)
        num = str(i)
        d.text((bx + 24 - d.textlength(num, font=bold(26)) / 2, by - 17), num, fill="#FFFFFF", font=bold(26))
        d.text((bx + 80, by - 22), text, fill=ink, font=regular(36))

    # Signature and stamp
    y = 1250
    d.line((M, y + 110, M + 420, y + 110), fill=muted, width=2)
    d.text((M + 10, y + 30), "A. Rao", fill="#2B3A67", font=font(64, "segoesc.ttf", "seguisb.ttf", "arial.ttf"))
    d.text((M, y + 122), "Dr. A. Rao, Consultant Obstetrician", fill=ink, font=regular(24))
    d.text((M, y + 154), "Signature", fill=muted, font=regular(20))
    sx, sy, r = W - M - 150, y + 90, 110
    stamp = Image.new("RGBA", (2 * r + 20, 2 * r + 20), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp)
    sd.ellipse((10, 10, 2 * r + 10, 2 * r + 10), outline=(46, 110, 115, 150), width=6)
    sd.ellipse((30, 30, 2 * r - 10, 2 * r - 10), outline=(46, 110, 115, 120), width=3)
    for t, ty, sz in (("LOTUS", r - 34, 34), ("CLINIC", r + 6, 30)):
        f = bold(sz)
        sd.text((r + 10 - sd.textlength(t, font=f) / 2, ty), t, fill=(46, 110, 115, 160), font=f)
    stamp = stamp.rotate(-14, resample=Image.BICUBIC)
    img.paste(stamp, (sx - r, sy - r), stamp)

    # Footer
    d.rectangle((0, H - 130, W, H), fill="#FBEDEE")
    msg = "Sample document for a demo, not a real prescription."
    d.text(((W - d.textlength(msg, font=bold(30))) / 2, H - 98), msg, fill="#A3283A", font=bold(30))
    sub = "Created for the With Us proof of concept. Not issued by any clinic."
    d.text(((W - d.textlength(sub, font=regular(22))) / 2, H - 52), sub, fill=muted, font=regular(22))

    img.save(settings.SEED_DIR / "discharge-sheet.png")


def ensure_demo() -> None:
    """On a fresh deployment, create the tables and the demo household once."""
    init_db()
    with Session(engine) as s:
        if s.exec(select(Household).where(Household.code == "meera")).first():
            return
    try:
        seed(drop=False)
    except Exception:  # another cold start seeded it at the same moment
        pass


def seed(cold: bool = False, drop: bool = True) -> Household:
    init_db(drop=drop)
    with Session(engine) as s:
        h = Household(code="meera", baby_type="girl", baby_name="Asha", baby_arrived="",
                      notes="C-section, two weeks ago.", week_start=this_monday(), cold=cold)
        s.add(h)
        s.commit()
        s.refresh(h)

        people = [
            ("meera", "Meera", "mother", 10, "--m1"),
            ("karan", "Karan", "partner", 12, "--m2"),
            ("ramesh", "Ramesh", "parent", 20, "--m3"),
            ("sunita", "Sunita", "relative", 14, "--m4"),
        ]
        ids = {}
        for slug, name, role, cap, colour in people:
            m = Member(household_id=h.id, slug=slug, name=name, role=role, capacity_hours=cap, colour=colour)
            s.add(m)
            s.commit()
            s.refresh(m)
            ids[slug] = m.id
        h.mother_member_id = ids["meera"]

        for day in ("Thu", "Fri"):
            lim = Limit(member_id=ids["karan"], kind="day", value=day, opaque_id=opaque())
            s.add(lim)
            s.commit()
            s.refresh(lim)
            s.add(PrivateReason(member_id=ids["karan"], limit_id=lim.id, text=KARAN_REASON))
        lim = Limit(member_id=ids["sunita"], kind="work_kind", value="Nights", opaque_id=opaque())
        s.add(lim)
        s.commit()
        s.refresh(lim)
        s.add(PrivateReason(member_id=ids["sunita"], limit_id=lim.id, text=SUNITA_REASON))
        s.add(AssistantInstructions(member_id=ids["meera"], text=MEERA_INSTRUCTIONS))
        s.add(RestWindow(member_id=ids["meera"], days=ALL, start="22:00", end="06:00"))
        s.add(RestWindow(member_id=ids["meera"], days=ALL, start="14:00", end="16:00"))
        s.add(MotherSharing(household_id=h.id, share_progress=True, share_with=[ids["karan"]]))

        preset = {}
        for title, kind, wk, days, start, end, hrs, travel, cold_only, owner in RESPONSIBILITIES:
            fixed = FIXED_OWNERS.get(title)
            r = Responsibility(household_id=h.id, title=title, kind=kind, work_kind=wk, days=days,
                               start=start, end=end, hours_per_occurrence=hrs, travel=travel,
                               cold_only=cold_only, source="family",
                               fixed_owner_id=ids[fixed] if fixed else None)
            s.add(r)
            s.commit()
            s.refresh(r)
            if owner:
                preset[r.id] = ids[owner]

        # Most of the week was already agreed; doctor visits and cooking are still being arranged.
        for rid, mid in preset.items():
            s.add(Proposal(responsibility_id=rid, member_id=mid, week=h.week_start, status="accepted"))
        h.sharing_ok_mother = True
        h.sharing_ok_partner = True
        s.add(h)
        s.commit()
        replan(s, h, note_activity=False)
        s.refresh(h)
        return h


if __name__ == "__main__":
    import sys

    make_discharge_sheet()
    h = seed(cold="--cold" in sys.argv)
    print(f"Seeded household '{h.code}' for week of {h.week_start}. Members: meera, karan, ramesh, sunita.")
