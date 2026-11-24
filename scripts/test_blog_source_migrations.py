#!/usr/bin/env python3
"""Pure regression tests for the reviewed Blog source migration guards."""

from copy import deepcopy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from blog_source_migrations import (  # noqa: E402
    ENGLISH_BICYCLE_TABLE_NEW,
    LOCALIZED_BICYCLE_TABLES,
    repair_english_table,
    repair_localized_table,
    render_table,
)


def main() -> None:
    post = {"buyerDecisionTable": {"rows": deepcopy(__import__("blog_source_migrations").ENGLISH_BICYCLE_TABLE_OLD)}}
    assert repair_english_table(post) == "changed"
    assert post["buyerDecisionTable"]["rows"] == ENGLISH_BICYCLE_TABLE_NEW
    assert repair_english_table(post) == "already-correct"

    conflict = {"buyerDecisionTable": {"rows": deepcopy(ENGLISH_BICYCLE_TABLE_NEW)}}
    conflict["buyerDecisionTable"]["rows"][0][0] = "Owner-approved custom row"
    try:
        repair_english_table(conflict)
    except ValueError:
        pass
    else:
        raise AssertionError("owner edits must not be overwritten")

    for locale, spec in LOCALIZED_BICYCLE_TABLES.items():
        old_html = render_table(spec["head_old"], spec["rows_old"])
        new_html, state = repair_localized_table(old_html, locale)
        assert state == "changed"
        assert repair_localized_table(new_html, locale)[1] == "already-correct"
        assert spec["head_new"][0] in new_html
    print("XUYI_BLOG_SOURCE_MIGRATION_TEST_PASSED")


if __name__ == "__main__":
    main()

