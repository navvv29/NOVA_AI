"""
Run with: python -m pytest tests/ -v

These only cover the tools that don't need network/API keys. They exist so
you can verify the repo itself is wired correctly before spending API quota.
"""

from src.tools.datetime_tool import get_current_datetime


def test_get_current_datetime_default_tz():
    result = get_current_datetime.invoke({})
    assert "Asia/Kolkata" in result


def test_get_current_datetime_custom_tz():
    result = get_current_datetime.invoke({"timezone": "America/New_York"})
    assert "America/New_York" in result


def test_get_current_datetime_invalid_tz_falls_back():
    result = get_current_datetime.invoke({"timezone": "Not/A_Real_Zone"})
    assert "fallback" in result
