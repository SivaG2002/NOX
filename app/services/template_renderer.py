from datetime import datetime
from typing import Any


class SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_template(template: str | None, values: dict[str, Any]) -> str:
    if not template:
        return ""
    normalized = {
        key: value.isoformat() if isinstance(value, datetime) else "" if value is None else value
        for key, value in values.items()
    }
    return template.format_map(SafeFormatDict(normalized))

