"""Database tables.

Private data (reasons, instructions, proposals, exclusions, chats, quest logs)
lives in its own tables. Only the owner's /api/me routes and the owner's own
AI context read them.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def now() -> datetime:
    return datetime.now()


class Household(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    mother_member_id: Optional[int] = None
    baby_type: str = "girl"  # girl | boy
    baby_name: str = ""
    baby_arrived: str = ""
    notes: str = ""
    week_start: str = ""
    tolerance_points: float = 15
    sharing_ok_mother: bool = False
    sharing_ok_partner: bool = False
    cold: bool = False


class Member(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(index=True)
    slug: str
    name: str
    role: str  # mother | partner | parent | relative | helper
    capacity_hours: float = 0
    colour: str = "--m1"


class Limit(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(index=True)
    kind: str  # day | work_kind
    value: str
    opaque_id: str


class PrivateReason(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(index=True)
    limit_id: Optional[int] = None
    text: str = ""


class AssistantInstructions(SQLModel, table=True):
    member_id: int = Field(primary_key=True)
    text: str = ""


class RestWindow(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(index=True)
    days: list = Field(default_factory=list, sa_column=Column(JSON))
    start: str = "14:00"
    end: str = "16:00"


class Responsibility(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(index=True)
    title: str
    kind: str  # recovery | baby | home
    work_kind: str = ""
    days: list = Field(default_factory=list, sa_column=Column(JSON))
    start: Optional[str] = None
    end: Optional[str] = None
    hours_per_occurrence: float = 1.0
    travel: bool = False
    fixed_owner_id: Optional[int] = None
    source: str = "family"  # prescription | family
    source_line: str = ""
    schedule: str = ""
    icon: str = ""  # walk | medicine | rest | wound | visit
    active: bool = True
    outside_help: bool = False
    cold_only: bool = False


class Prescription(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(index=True)
    image_path: str = ""
    text: str = ""
    extracted_json: list = Field(default_factory=list, sa_column=Column(JSON))
    used_ai: bool = False
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None


class QuestLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(index=True)
    quest_key: str
    date: str
    done_at: datetime = Field(default_factory=now)


class MotherSharing(SQLModel, table=True):
    household_id: int = Field(primary_key=True)
    share_progress: bool = False
    share_with: list = Field(default_factory=list, sa_column=Column(JSON))


class Proposal(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    responsibility_id: int = Field(index=True)
    member_id: int = Field(index=True)
    week: str
    status: str = "pending"  # pending | accepted | declined | withdrawn
    created_at: datetime = Field(default_factory=now)


class Exclusion(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(index=True)
    responsibility_id: int
    week: str


class Plan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(index=True)
    week: str
    version: int = 1
    published_at: datetime = Field(default_factory=now)
    assignments_json: list = Field(default_factory=list, sa_column=Column(JSON))
    burden_json: list = Field(default_factory=list, sa_column=Column(JSON))
    unassigned_json: list = Field(default_factory=list, sa_column=Column(JSON))
    arranging_json: list = Field(default_factory=list, sa_column=Column(JSON))
    spread: float = 0
    headline: str = ""


class Decision(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(index=True)
    type: str = "shortfall"
    payload_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: str = "open"  # open | resolved
    resolved_option: str = ""


class Activity(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(index=True)
    at: datetime = Field(default_factory=now)
    text: str


class ChatMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    member_id: int = Field(index=True)
    role: str  # user | assistant
    text: str
    at: datetime = Field(default_factory=now)


class Announcement(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    household_id: int = Field(index=True)
    from_member_id: int
    text: str
    at: datetime = Field(default_factory=now)


class SessionToken(SQLModel, table=True):
    token_hash: str = Field(primary_key=True)
    member_id: int = Field(index=True)
    created_at: datetime = Field(default_factory=now)
