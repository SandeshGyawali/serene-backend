from datetime import datetime, date, timedelta


def get_period(time_str: str) -> str:
    """Return Morning / Afternoon / Evening based on HH:MM."""
    try:
        hour = int(time_str.split(":")[0])
    except (ValueError, IndexError):
        return "Morning"
    if hour < 12:
        return "Morning"
    if hour < 17:
        return "Afternoon"
    return "Evening"


def time_diff_minutes(scheduled_time: str, actual_dt: datetime, log_date: date) -> float:
    """How many minutes late (positive) or early (negative) compared to schedule."""
    try:
        hour, minute = map(int, scheduled_time.split(":"))
        scheduled_dt = datetime.combine(log_date, datetime.min.time().replace(hour=hour, minute=minute))
        delta = (actual_dt - scheduled_dt).total_seconds() / 60
        return round(delta, 2)
    except Exception:
        return 0.0


def calc_xp(base_xp: int, time_diff: float) -> tuple[int, float, str]:
    """Return (xp_earned, xp_percent, timing_feedback)."""
    if time_diff <= 5:
        percent = 1.0
        feedback = "Perfect timing! Full XP awarded."
    elif time_diff <= 15:
        percent = 0.85
        feedback = "Slightly late — solid effort."
    elif time_diff <= 30:
        percent = 0.65
        feedback = "Late start, but you showed up."
    elif time_diff <= 60:
        percent = 0.45
        feedback = "Significantly delayed. Better tomorrow."
    else:
        percent = 0.25
        feedback = "Very late. The Oracle notes your struggle."

    earned = max(1, round(base_xp * percent))
    return earned, percent, feedback


def calc_duration_feedback(minutes: float) -> str:
    if minutes < 5:
        return "Lightning fast — suspicious, but recorded."
    if minutes < 20:
        return "Quick and efficient."
    if minutes < 60:
        return "Solid session."
    if minutes < 120:
        return "Extended focus. Respect."
    return "Marathon session. Rest well after this."


def calc_level(xp: int) -> int:
    return 1 + xp // 500
