from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from langchain_core.tools import tool

DEFAULT_TZ = "Asia/Kolkata"


@tool
def get_current_datetime(timezone: str = DEFAULT_TZ) -> str:
    """Get the current date and time.

    Defaults to IST (Asia/Kolkata). Pass a different IANA timezone string
    (e.g. "America/New_York") if the user asks about another timezone.
    """
    try:
        now = datetime.now(ZoneInfo(timezone))
    except ZoneInfoNotFoundError:
        now = datetime.now(ZoneInfo(DEFAULT_TZ))
        timezone = f"{DEFAULT_TZ} (fallback — '{timezone}' wasn't a valid timezone)"

    return f"{now.strftime('%A, %d %B %Y, %I:%M %p')} ({timezone})"
