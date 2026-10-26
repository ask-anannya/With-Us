"""Log in as each seed member, call every GET endpoint, and check that no other
member's private reason, instruction, proposal or decline appears anywhere."""
import json

from app.seed import KARAN_REASON, MEERA_INSTRUCTIONS, SUNITA_REASON

from .conftest import SLUGS

SECRETS = {"karan": [KARAN_REASON], "sunita": [SUNITA_REASON], "meera": [MEERA_INSTRUCTIONS]}
FRAGMENTS = {"karan": ["Client meetings", "exhausted"], "sunita": ["light sleeper"], "meera": ["never say no"]}

GETS = ["/api/household", "/api/me", "/api/plan", "/api/responsibilities", "/api/me/proposals",
        "/api/decisions", "/api/activity", "/api/announcements", "/api/quests/today",
        "/api/quests/progress", "/api/me/what-household-sees", "/api/me/what-assistant-is-told",
        "/api/assistant/history"]


def everything_seen_by(client) -> str:
    out = []
    for path in GETS:
        r = client.get(path)
        if r.status_code == 200:
            out.append(json.dumps(r.json()))
    return "\n".join(out).lower()


def assert_no_secrets_of_others(viewer: str, seen: str):
    for owner in SLUGS:
        if owner == viewer:
            continue
        for text in SECRETS.get(owner, []) + FRAGMENTS.get(owner, []):
            assert text.lower() not in seen, f"{viewer} can see {owner}'s private text: {text!r}"


def test_no_private_text_leaks_across_members(as_member):
    for viewer in SLUGS:
        assert_no_secrets_of_others(viewer, everything_seen_by(as_member(viewer)))


def test_owner_sees_their_own_reason(as_member):
    me = as_member("karan").get("/api/me").json()
    assert any(l["reason"] == KARAN_REASON for l in me["limits"])
    sees = as_member("karan").get("/api/me/what-household-sees").json()
    assert "Client meetings" not in json.dumps(sees)
    assert {l["value"] for l in sees["limits"]} == {"Thu", "Fri"}


def test_proposals_and_declines_stay_private(as_member):
    ramesh = as_member("ramesh")
    mine = ramesh.get("/api/me/proposals").json()
    titles = {p["responsibility"]["title"]: p["id"] for p in mine}
    assert "Cooking" in titles
    # nobody else sees Ramesh's proposals
    for other in ("meera", "karan", "sunita"):
        assert str(titles["Cooking"]) not in [str(p["id"]) for p in as_member(other).get("/api/me/proposals").json()]
    ramesh.post(f"/api/me/proposals/{titles['Cooking']}/decline", json={"tell_family": False})
    for viewer in ("meera", "karan", "sunita"):
        seen = everything_seen_by(as_member(viewer))
        assert "declined" not in seen
        assert_no_secrets_of_others(viewer, seen)
        plan = as_member(viewer).get("/api/plan").json()
        cooking = [a for a in plan["assignments"] if a["responsibility"]["title"] == "Cooking"]
        assert not cooking or cooking[0]["member_name"] != "Ramesh"
    acts = as_member("sunita").get("/api/activity").json()
    assert all(a["text"] in ("Plan updated", "A task was added", "Doctor's instructions confirmed") for a in acts)
