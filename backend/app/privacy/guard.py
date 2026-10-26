"""Output guard: a backup layer that runs on every AI output and Announcement.

The assistants never receive other people's private text in the first place;
this catches anything that slips through anyway. Logs a count, never the text.
"""
import base64
import binascii
import logging
import re
import unicodedata

log = logging.getLogger("with_us.guard")
BLOCK_COUNT = {"n": 0}

SAFE_FALLBACK = "That's theirs to share. I can only tell you what's in the plan."

ZERO_WIDTH = re.compile("[​‌‍⁠﻿­]")
LOOKALIKES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j",
    "ѕ": "s", "ԁ": "d", "ɡ": "g", "һ": "h", "ӏ": "l", "ո": "n", "ս": "u", "ν": "v", "ο": "o",
    "α": "a", "ε": "e", "ι": "i", "κ": "k", "ρ": "p", "τ": "t", "υ": "u", "χ": "x",
    "0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s", "!": "i",
})
B64_RUN = re.compile(r"[A-Za-z0-9+/]{12,}={0,2}")
HEX_RUN = re.compile(r"\b(?:[0-9a-fA-F]{2}[\s:]?){6,}\b")
SPACED = re.compile(r"\b(?:[a-z][\s\-._*]+){3,}[a-z]\b")
WORD = re.compile(r"[a-z']+")

# Common words that carry no secret on their own.
STOPWORDS = {
    "about", "after", "again", "always", "around", "because", "before", "being", "can't", "cant",
    "could", "doesn't", "every", "found", "going", "haven't", "havent", "having", "isn't", "might",
    "never", "other", "really", "should", "since", "still", "their", "there", "these", "thing",
    "things", "think", "those", "through", "under", "until", "wasn't", "where", "which", "while",
    "would", "words", "you're", "they're", "won't", "don't", "didn't", "can't", "please", "today",
    "tomorrow", "week", "weeks", "help", "family", "plan", "tasks", "household", "person", "people",
}


def _decode_runs(text: str) -> str:
    extra = []
    for run in B64_RUN.findall(text):
        try:
            raw = base64.b64decode(run + "=" * (-len(run) % 4), validate=False)
            dec = raw.decode("utf-8")
            if dec and sum(c.isprintable() for c in dec) / len(dec) > 0.9:
                extra.append(dec)
        except (binascii.Error, UnicodeDecodeError, ValueError):
            pass
    for run in HEX_RUN.findall(text):
        digits = re.sub(r"[\s:]", "", run)
        try:
            dec = bytes.fromhex(digits).decode("utf-8")
            if dec and sum(c.isprintable() for c in dec) / len(dec) > 0.9:
                extra.append(dec)
        except (ValueError, UnicodeDecodeError):
            pass
    return text + (" " + " ".join(extra) if extra else "")


def normalise(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "")
    t = ZERO_WIDTH.sub("", t)
    t = _decode_runs(t)
    t = t.lower().replace("’", "'").translate(LOOKALIKES)
    t = SPACED.sub(lambda m: re.sub(r"[\s\-._*]", "", m.group(0)), t)
    return re.sub(r"\s+", " ", t).strip()


def _words(text: str) -> list:
    return [w.strip("'") for w in WORD.findall(text) if w.strip("'")]


def leaks(output: str, protected: list, allowed: set | None = None) -> bool:
    allowed = {a.lower() for a in (allowed or set())}
    out = normalise(output)
    out_words = _words(out)
    out_set = set(out_words)
    out_trigrams = {tuple(out_words[i:i + 3]) for i in range(len(out_words) - 2)}
    for secret in protected:
        if not secret:
            continue
        sw = _words(normalise(secret))
        for i in range(len(sw) - 2):
            tri = tuple(sw[i:i + 3])
            # a run made only of public words and short fillers ("thursday and friday") carries no secret
            if tri in out_trigrams and not all(w in allowed or w in STOPWORDS or len(w) <= 3 for w in tri):
                return True
        for w in sw:
            if len(w) >= 5 and w not in STOPWORDS and w not in allowed and w in out_set:
                return True
    return False


def check(output: str, protected: list, allowed: set | None = None, fallback: str = SAFE_FALLBACK) -> str:
    if output and leaks(output, protected, allowed):
        BLOCK_COUNT["n"] += 1
        log.warning("guard blocked an output (total %d)", BLOCK_COUNT["n"])
        return fallback
    return output
