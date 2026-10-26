"""Weights, capacity and burden. Plain arithmetic, no AI."""

MOTHER_CEILING = 0.5  # we plan the mother at half of what she states
NIGHTS_MULTIPLIER = 1.5
TRAVEL_MULTIPLIER = 1.2

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WORK_KINDS = ["Nights", "Driving", "Cooking", "Appointments", "Baby care", "Cleaning", "Errands"]


def multiplier(work_kind: str, travel: bool) -> float:
    if work_kind == "Nights":
        return NIGHTS_MULTIPLIER
    if travel or work_kind == "Driving":
        return TRAVEL_MULTIPLIER
    return 1.0


def hours_per_week(hours_per_occurrence: float, days: list) -> float:
    return hours_per_occurrence * len(days)


def weight(hours_per_occurrence: float, days: list, work_kind: str, travel: bool) -> float:
    return hours_per_week(hours_per_occurrence, days) * multiplier(work_kind, travel)


def effective_capacity(capacity_hours: float, is_mother: bool) -> float:
    return capacity_hours * MOTHER_CEILING if is_mother else capacity_hours


def burden(assigned_weight: float, eff_capacity: float) -> float:
    """Share of a person's own capacity, as a fraction (0.5 = 50%)."""
    if eff_capacity <= 0:
        return 0.0
    return assigned_weight / eff_capacity
