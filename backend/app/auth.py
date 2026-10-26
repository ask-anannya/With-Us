"""Household code + member ID sign-in, held in an httpOnly session cookie."""
import hashlib
import secrets

from fastapi import Depends, HTTPException, Request, Response
from sqlmodel import Session, select

from .db import get_session
from .models import Household, Member, SessionToken

COOKIE = "wu_session"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(s: Session, response: Response, member: Member) -> None:
    token = secrets.token_urlsafe(32)
    s.add(SessionToken(token_hash=_hash(token), member_id=member.id))
    s.commit()
    from . import settings

    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=settings.ON_VERCEL,
                        max_age=60 * 60 * 24 * 30)


def end_session(s: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        row = s.get(SessionToken, _hash(token))
        if row:
            s.delete(row)
            s.commit()
    response.delete_cookie(COOKIE)


def current_member(request: Request, s: Session = Depends(get_session)) -> Member:
    token = request.cookies.get(COOKIE)
    row = s.get(SessionToken, _hash(token)) if token else None
    member = s.get(Member, row.member_id) if row else None
    if not member:
        raise HTTPException(401, "Please sign in with your household code and member ID.")
    return member


def household_of(s: Session, m: Member) -> Household:
    return s.get(Household, m.household_id)


def find_member(s: Session, h: Household, slug: str) -> Member | None:
    return s.exec(select(Member).where(Member.household_id == h.id, Member.slug == slug)).first()


def require_mother_or_partner(h: Household, m: Member) -> None:
    if not (m.id == h.mother_member_id or m.role == "partner"):
        raise HTTPException(403, "Only the mother or partner can do that.")
