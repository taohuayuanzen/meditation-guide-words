from datetime import UTC, datetime


def utc_now() -> datetime:
    """返回当前 UTC 时间，替代已弃用的 datetime.utcnow。"""
    return datetime.now(UTC)
