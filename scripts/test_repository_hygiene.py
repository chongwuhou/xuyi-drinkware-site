"""Keep the repository focused on current generic entrypoints and sources.

Historical Blog batch publishers, dated source registries and dated live
verification scripts must not return. D1/CMS and the canonical JSON sources
are the only supported content boundaries.
"""
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN=(
    re.compile(r"^scripts/(?:prepare_blog_(?:release|covers|images)|publish_blog_(?:batch|covers|images|translation_repair)|schedule_blog_batch)_20\d+"),
    re.compile(r"^scripts/(?:test_20\d+|test_blog_20\d+|verify_live_blog_20\d+)"),
    re.compile(r"^scripts/test_blog_(?:covers|index_order|localized_schedule|schedule|translation_repair)_20\d+"),
    re.compile(r"^functions/api/admin/blog-(?:batch|covers|images|index-(?:copy|heading)-cleanup|refresh|schedule|translation-repair)-20\d+"),
    re.compile(r"^functions/api/admin/(?:blog-seo-phase2-corrections|collection-seo-refresh|product-seo-(?:promotion|refresh))"),
    re.compile(r"^scripts/(?:publish|verify)_owner_.*20\d{6}.*\.py$"),
    re.compile(r"^data/blog-guides-20\d{6}(?:-\d+)?\.json$"),
    re.compile(r"^data/blog-photo-(?:context-)?corrections-20\d{6}\.json$"),
)
REQUIRED=(
    "functions/api/admin/blog-batch.js",
    "functions/api/admin/blog-media.js",
    "scripts/build_release.py",
    "scripts/fetch_build_snapshot.py",
    "scripts/test_pages_functions_syntax.py",
    "scripts/blog_source_migrations.py",
    "scripts/repair_blog_source.py",
    "scripts/test_blog_source_migrations.py",
    "docs/XUYI_OPERATIONAL_RUNBOOK_ZH.md",
    "data/blog-guides.json",
    "data/blog-photo-corrections.json",
)
paths=[p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts]
bad=[path for path in paths if any(pattern.search(path) for pattern in FORBIDDEN)]
missing=[path for path in REQUIRED if not (ROOT/path).is_file()]
if bad:
    print("::error::forbidden historical entrypoints remain:")
    print("\n".join(bad))
    sys.exit(1)
if missing:
    raise SystemExit("missing generic entrypoint: "+", ".join(missing))
print("XUYI_REPOSITORY_HYGIENE_PASSED",len(paths),"files")

