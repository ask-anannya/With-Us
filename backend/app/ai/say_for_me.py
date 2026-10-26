"""Say it for me: one kind sentence. Sees only first name, task title and week."""
from pydantic import BaseModel

from .client import generate_json

SYSTEM = (
    "You write one short, kind sentence a family member can share when they can't take a task this "
    "week. At most 25 words. Third person, using their first name. No reason, no blame, no heavy "
    "apology, no em dashes. Warm and light. Example: \"Karan can't take Saturday groceries this "
    "week. He's grateful to whoever can.\" Do not use he or she unless the example pattern fits; "
    "prefer the name or 'they'."
)


class Line(BaseModel):
    sentence: str


def template(name: str, task: str) -> str:
    return f"{name} can't take {task.lower()} this week."


def write(name: str, task: str) -> str:
    out = generate_json(SYSTEM, [f"First name: {name}\nTask: {task}\nWeek: this week"], Line, temperature=0.6)
    if not out or not out.sentence.strip():
        return template(name, task)
    line = out.sentence.strip().replace("—", ",").replace("–", ",")
    if len(line.split()) > 25:
        return template(name, task)
    return line
