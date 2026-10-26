from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..ai import assistant as ai
from ..auth import current_member, household_of
from ..db import get_session
from ..models import AssistantInstructions, ChatMessage, Member, PrivateReason
from ..planning import members_of
from ..privacy import guard
from .plan import my_proposals

router = APIRouter(prefix="/api")


class ChatBody(BaseModel):
    message: str


def protected_texts(s: Session, h, me: Member) -> list:
    """Other members' private text that this member's assistant must never output."""
    others = [m.id for m in members_of(s, h) if m.id != me.id]
    texts = [r.text for r in s.exec(select(PrivateReason).where(PrivateReason.member_id.in_(others))).all()]
    texts += [i.text for i in s.exec(select(AssistantInstructions)
                                     .where(AssistantInstructions.member_id.in_(others))).all()]
    return texts


def fallback(proposals: list) -> dict:
    if proposals:
        text = ("I can't think clearly right now, but here's what's waiting on you. "
                "You can answer each one with the buttons.")
        actions = []
        for p in proposals:
            t = p["responsibility"]["title"]
            actions.append({"type": "accept", "proposal_id": p["id"], "label": f"Take {t}"})
            actions.append({"type": "decline", "proposal_id": p["id"], "label": f"Not this week: {t}"})
        return {"reply": text, "actions": actions}
    return {"reply": ("I can't think clearly right now. Nothing is waiting on you, and your week is in "
                      "the plan. You can change your limits in the Control panel."), "actions": []}


def answer(s: Session, h, me: Member, message: str, store: bool = True) -> dict:
    if ai.is_crisis(message):
        # Never stored, never summarised.
        return {"crisis": True, "reply": ai.HELP_LINE, "actions": []}
    proposals = my_proposals(s, h, me)
    history = [(c.role, c.text) for c in s.exec(select(ChatMessage).where(ChatMessage.member_id == me.id)
                                                 .order_by(ChatMessage.id.desc()).limit(10)).all()][::-1]
    context = ai.build_context(s, h, me, proposals)
    out = ai.reply(context, history, message)
    used_ai = out is not None
    if out is None:
        result = fallback(proposals)
    else:
        mine = {p["id"]: p for p in proposals}
        actions = []
        for a in out.actions:
            if a.type in ("accept", "decline") and a.proposal_id in mine:
                t = mine[a.proposal_id]["responsibility"]["title"]
                actions.append({"type": a.type, "proposal_id": a.proposal_id,
                                "label": a.label or (f"Take {t}" if a.type == "accept" else f"Not this week: {t}")})
            elif a.type == "update_limit" and a.kind in ("day", "work_kind") and a.value:
                actions.append({"type": "update_limit", "kind": a.kind, "value": a.value,
                                "label": a.label or f"Add limit: {a.value}"})
        result = {"reply": out.reply.replace("—", ",").strip(), "actions": actions}
    result["reply"] = guard.check(result["reply"], protected_texts(s, h, me), ai.public_vocabulary(s, h))
    for a in result["actions"]:
        a["label"] = guard.check(a["label"], protected_texts(s, h, me), ai.public_vocabulary(s, h), fallback="Suggested step")
    result["used_ai"] = used_ai
    if store:
        s.add(ChatMessage(member_id=me.id, role="user", text=message))
        s.add(ChatMessage(member_id=me.id, role="assistant", text=result["reply"]))
        s.commit()
    return result


@router.post("/assistant")
def chat(body: ChatBody, me: Member = Depends(current_member), s: Session = Depends(get_session)):
    if not body.message.strip():
        raise HTTPException(400, "Type a message first.")
    h = household_of(s, me)
    return answer(s, h, me, body.message.strip()[:2000])


@router.get("/assistant/history")
def history(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    rows = s.exec(select(ChatMessage).where(ChatMessage.member_id == me.id).order_by(ChatMessage.id)).all()
    return [{"role": c.role, "text": c.text} for c in rows[-40:]]


@router.delete("/assistant/history")
def clear(me: Member = Depends(current_member), s: Session = Depends(get_session)):
    for c in s.exec(select(ChatMessage).where(ChatMessage.member_id == me.id)).all():
        s.delete(c)
    s.commit()
    return {"ok": True}
