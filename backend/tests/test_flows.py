from fastapi.testclient import TestClient

from app.main import app
from app.seed import SHEET_LINES


def titles(proposals):
    return {p["responsibility"]["title"]: p["id"] for p in proposals}


def test_seed_plan_is_published(as_member):
    plan = as_member("ramesh").get("/api/plan").json()
    assert plan["ready"] and plan["headline"]
    arranging = {r["title"] for r in plan["arranging"]}
    assert {"Cooking", "Baby's doctor visits"} <= arranging
    assert all("member_id" not in r for r in plan["arranging"])


def test_gate_blocks_until_both_switches(as_member):
    meera, karan = as_member("meera"), as_member("karan")
    karan.patch("/api/household/sharing", json={"on": False})
    assert as_member("ramesh").get("/api/plan").json()["ready"] is False
    assert as_member("ramesh").post("/api/plan/replan").status_code == 409
    assert as_member("ramesh").patch("/api/household/sharing", json={"on": True}).status_code == 403
    karan.patch("/api/household/sharing", json={"on": True})
    assert meera.get("/api/plan").json()["ready"] is True


def test_accept_decline_and_cold_shortfall(as_member):
    ramesh = as_member("ramesh")
    mine = titles(ramesh.get("/api/me/proposals").json())
    assert ramesh.post(f"/api/me/proposals/{mine['Baby' + chr(39) + 's doctor visits']}/accept").status_code == 200
    r = ramesh.post(f"/api/me/proposals/{mine['Cooking']}/decline", json={"tell_family": True})
    assert r.status_code == 200
    line = r.json()["announcement"]
    assert line and "Ramesh" in line and len(line.split()) <= 25

    plan = as_member("sunita").get("/api/plan").json()
    owners = {a["responsibility"]["title"]: a["member_name"] for a in plan["assignments"]}
    assert owners["Baby's doctor visits"] == "Ramesh"
    assert "Cooking" in titles(as_member("sunita").get("/api/me/proposals").json())
    assert "Cooking" not in titles(ramesh.get("/api/me/proposals").json())

    as_member("karan").post("/api/household/cold", json={"on": True})
    decisions = as_member("sunita").get("/api/decisions").json()
    assert len(decisions) == 1
    d = decisions[0]
    assert d["hours"] == 3.0 and "still need someone" in d["text"]
    assert "drop" not in d["options"]
    assert "Ramesh" not in d["text"] and "Sunita" not in d["text"]
    assert "drop" in as_member("karan").get("/api/decisions").json()[0]["options"]
    assert as_member("sunita").post(f"/api/decisions/{d['id']}/resolve", json={"option": "drop"}).status_code == 403
    assert as_member("sunita").post(f"/api/decisions/{d['id']}/resolve",
                                    json={"option": "outside_help"}).status_code == 200
    plan = as_member("karan").get("/api/plan").json()
    assert plan["unassigned"] == []
    assert any(r["title"].startswith("Pediatric") for r in plan["outside_help"])


def test_capacity_is_own_only(as_member):
    karan = as_member("karan")
    karan.put("/api/me/profile", json={"capacity_hours": 16})
    me = as_member("ramesh").get("/api/household").json()
    caps = {m["name"]: m["capacity_hours"] for m in me["members"]}
    assert caps["Karan"] == 16 and caps["Ramesh"] == 20


def test_prescription_fallback_confirm_and_quests(as_member):
    karan = as_member("karan")
    text = "\n".join(SHEET_LINES)
    r = karan.post("/api/prescription", data={"text": text})
    assert r.status_code == 200
    body = r.json()
    assert body["used_ai"] is False and len(body["items"]) == 4
    items = body["items"]
    for it in items:
        it["days"] = it["days"] or ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    assert karan.post(f"/api/prescription/{body['id']}/confirm", json={"items": items}).json()["created"] == 4
    assert as_member("karan").get("/api/quests/today").status_code == 403
    today = as_member("meera").get("/api/quests/today").json()
    recovery = [q for q in today["quests"] if q["kind"] == "recovery"]
    rest = [q for q in today["quests"] if q["kind"] == "rest"]
    assert len(recovery) == 4 and len(rest) == 2
    assert all(q["original_line"] in SHEET_LINES for q in recovery)
    assert today["bunnies"] == 0
    done = as_member("meera").post(f"/api/quests/{recovery[0]['key']}/done").json()
    assert done["bunnies"] == 1
    # Karan has quest sharing, Ramesh does not
    shared = as_member("karan").get("/api/quests/progress").json()
    assert shared["shared"] and shared["done"] == 1 and shared["total"] == 6 and shared["bunnies"] == 1
    assert {q["title"] for q in shared["quests"]} >= set(SHEET_LINES)
    assert as_member("ramesh").get("/api/quests/progress").json() == {"shared": False, "quests": [], "dots": []}


def test_create_and_join_household(seeded):
    a, b = TestClient(app), TestClient(app)
    r = a.post("/api/households", json={"baby_type": "boy", "mother_name": "Priya", "baby_name": "Dev",
                                        "creator_is_mother": False, "creator_name": "Arjun",
                                        "creator_role": "partner"})
    assert r.status_code == 200
    code, mid = r.json()["code"], r.json()["member_id"]
    assert mid == "arjun"
    j = b.post("/api/session", json={"code": code, "member_id": "", "name": "Lata", "role": "parent"})
    assert j.status_code == 200 and j.json()["created"]
    hh = b.get("/api/household").json()
    assert hh["baby_type"] == "boy" and {m["name"] for m in hh["members"]} == {"Priya", "Arjun", "Lata"}
    assert TestClient(app).post("/api/session", json={"code": code, "member_id": "nobody"}).status_code == 404


def test_assistant_fallback_and_crisis(as_member):
    ramesh = as_member("ramesh")
    r = ramesh.post("/api/assistant", json={"message": "Why is Karan never free on Thursdays?"}).json()
    assert "Client" not in r["reply"]
    crisis = ramesh.post("/api/assistant", json={"message": "I want to die"}).json()
    assert crisis["crisis"] and "14416" in crisis["reply"]
    hist = ramesh.get("/api/assistant/history").json()
    assert all("want to die" not in m["text"] for m in hist)
