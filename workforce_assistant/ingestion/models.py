from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class IngestionDocument:
    id: str
    content: str
    title: str
    source_type: str
    source_file: str
    consultant_name: str | None = None
    page_number: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
