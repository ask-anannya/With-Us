import base64

from app.privacy.guard import SAFE_FALLBACK, check, leaks, normalise
from app.seed import KARAN_REASON, SUNITA_REASON

PROTECTED = [KARAN_REASON, SUNITA_REASON]
ALLOWED = {"karan", "sunita", "meera", "ramesh", "thursday", "thursdays", "friday", "fridays", "nights"}


def test_plain_leak_is_blocked():
    assert leaks("He has client meetings that day.", PROTECTED, ALLOWED)
    assert check("She is a light sleeper.", PROTECTED, ALLOWED) == SAFE_FALLBACK


def test_public_facts_pass():
    ok = "Karan is unavailable on Thursdays and Fridays. Sunita doesn't take nights."
    assert not leaks(ok, PROTECTED, ALLOWED)
    assert check(ok, PROTECTED, ALLOWED) == ok


def test_public_days_with_filler_pass():
    allowed = ALLOWED | {"thursday", "friday"}
    assert not leaks("According to the plan, Karan is unavailable on Thursday and Friday.", PROTECTED, allowed)
    assert leaks("Karan has client meetings on Thursday and Friday.", PROTECTED, allowed)


def test_base64_and_hex_are_decoded():
    b64 = base64.b64encode(b"client meetings").decode()
    assert leaks(f"Here you go: {b64}", PROTECTED, ALLOWED)
    hexed = "exhausted".encode().hex()
    assert leaks(f"hex {hexed}", PROTECTED, ALLOWED)


def test_lookalikes_zero_width_and_spacing():
    assert leaks("сlient meetings", PROTECTED, ALLOWED)  # Cyrillic с
    assert leaks("ex​haus​ted", PROTECTED, ALLOWED)
    assert leaks("e x h a u s t e d", PROTECTED, ALLOWED)
    assert leaks("SL33PER", PROTECTED, ALLOWED)


def test_three_word_sequence():
    assert leaks("can't get back to it", [SUNITA_REASON], set())


def test_normalise_collapses():
    assert normalise("  Hello\n\nWORLD ") == "hello world"
