"""The dashboard headline. Written by code, never by AI."""


def headline(mother_name: str, burden: dict, names: dict, spread: float,
             unassigned_hours: float, tolerance: float) -> str:
    if unassigned_hours > 0:
        hours = max(1, round(unassigned_hours))
        return f"{hours} hour{'s' if hours != 1 else ''} a week still need{'s' if hours == 1 else ''} someone."
    if spread > tolerance and burden:
        top = max(sorted(burden), key=lambda mid: burden[mid])
        return f"{names[top]} is carrying the most this week."
    return f"The week is shared fairly. {mother_name}'s rest is protected."
