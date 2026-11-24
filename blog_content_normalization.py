"""Small, deterministic normalizers for database-owned Blog section copy.

The CMS remains the source of truth. These functions only remove an exact
paragraph that has already appeared earlier in the same article, which keeps
owner content intact while preventing a repeated template disclaimer from
being rendered seven times. They do not translate, invent, or reorder copy.
"""
from __future__ import annotations

import copy
import re


def dedupe_section_paragraphs(sections):
    """Return section copies with repeated long paragraphs emitted once.

    Section headings, indexes, and all non-duplicate text are preserved. A
    paragraph is considered duplicate only after whitespace normalization and
    only when it is long enough to be a boilerplate block rather than a short
    label or buyer instruction.
    """
    seen = set()
    result = []
    for section in sections or []:
        if not isinstance(section, dict):
            result.append(copy.deepcopy(section))
            continue
        value = str(section.get("paragraph") or "")
        parts = [part.strip() for part in re.split(r"\n\s*\n", value.strip()) if part.strip()]
        kept = []
        for part in parts:
            key = re.sub(r"\s+", " ", part).strip().casefold()
            if len(key) >= 80 and key in seen:
                continue
            if key:
                seen.add(key)
            kept.append(part)
        item = copy.deepcopy(section)
        item["paragraph"] = "\n\n".join(kept)
        result.append(item)
    return result

