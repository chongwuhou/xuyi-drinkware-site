#!/usr/bin/env python3
"""Fast, dependency-free guard for the canonical human/AI operating contract."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "XUYI_OPERATIONAL_RUNBOOK_ZH.md"
POINTERS = [
    ROOT / "AGENTS.md",
    ROOT / "PROJECT_CHANGE_POLICY.md",
    ROOT / "README.md",
    ROOT / "docs" / "AI_COLLABORATION_QUICKSTART_ZH.md",
    ROOT / "项目圣经" / "目录.md",
]
REQUIRED_SECTIONS = (
    "## 1. 永久边界",
    "## 2. 所有任务的统一状态",
    "## 3. 开工前固定读取顺序",
    "## 4. 两种执行模式",
    "## 5. 任务与正式入口",
    "## 6. D1/R2 写入前检查",
    "## 7. Blog 固定标准",
    "## 8. 产品、SEO、翻译和图片固定标准",
    "## 9. 发布、失败和回滚",
    "## 10. 交接记录模板",
    "## 11. 给任何 AI 或新操作员的固定指令",
)
FORBIDDEN_IN_CANONICAL = (
    "默认 en/es/pt/ru/tr",
    "五语页面",
    "五语言核验",
)

def fail(message: str) -> None:
    print(f"::error::{message}")
    sys.exit(1)

if not RUNBOOK.is_file():
    fail("missing canonical operating runbook")

runbook = RUNBOOK.read_text(encoding="utf-8")
missing = [section for section in REQUIRED_SECTIONS if section not in runbook]
if missing:
    fail("runbook missing sections: " + ", ".join(missing))
if "用户明确授权" not in runbook or "AI 不操作浏览器" not in runbook:
    fail("runbook is missing the authorization/browser boundary")
for token in FORBIDDEN_IN_CANONICAL:
    if token in runbook:
        fail(f"hardcoded live value remains in runbook: {token}")

for path in POINTERS:
    if not path.is_file():
        fail(f"missing handoff/policy file: {path.relative_to(ROOT)}")
    text = path.read_text(encoding="utf-8")
    if "XUYI_OPERATIONAL_RUNBOOK_ZH.md" not in text:
        fail(f"file does not point to the canonical runbook: {path.relative_to(ROOT)}")

quickstart = (ROOT / "docs" / "AI_COLLABORATION_QUICKSTART_ZH.md").read_text(encoding="utf-8")
if re.search(r"默认\s*(en/es/pt/ru/tr)|五语页面|五语言核验", quickstart):
    fail("quickstart still contains a fixed locale-count instruction")

workflow = (ROOT / ".github" / "workflows" / "publish-xuyi.yml").read_text(encoding="utf-8")
if "schedule_blog_20261103" in workflow:
    fail("historical date-specific workflow input remains")
if re.search(r"^\s*- name: (?:Prepare|Publish|Upload|Repair|Schedule|Rebuild|Double).*20\d{2}", workflow, re.MULTILINE):
    fail("historical date-specific release step remains in the live publisher")

workflow = (ROOT / ".github" / "workflows" / "publish-xuyi.yml").read_text(encoding="utf-8")
if "schedule_blog_20261103" in workflow:
    fail("historical date-specific workflow input remains")
if re.search(r"^\s*- name: (?:Prepare|Publish|Upload|Repair|Schedule|Rebuild|Double).*20\d{2}", workflow, re.MULTILINE):
    fail("historical date-specific release step remains in the live publisher")
if re.search(r"scripts/[^\s]*20\d{2}", workflow):
    fail("historical date-specific script remains in the live publisher")
if re.search(r"(?i)(?:five|four|fifteen|twenty)[ -]language", workflow):
    fail("fixed locale batch wording remains in the live publisher")


if "Bootstrap reviewed Blog cleanup endpoint" in workflow:
    fail("one-time Blog cleanup publisher remains in the live workflow")
if "Apply reviewed localized Blog index and copy cleanup" in workflow:
    fail("one-time Blog index cleanup remains in the live workflow")
if "Bootstrap reviewed Blog SEO phase-two correction endpoint" in workflow:
    fail("one-time Blog SEO publisher remains in the live workflow")
if "Apply reviewed Blog SEO phase-two D1 corrections" in workflow:
    fail("one-time Blog SEO correction remains in the live workflow")
if "cancel-in-progress: true" not in workflow:
    fail("superseded production runs are not cancelled")
if "scripts/test_pages_functions_syntax.py" not in workflow:
    fail("Pages Function syntax gate is missing")
if "scripts/test_blog_card_contract.py" not in workflow:
    fail("Blog card compatibility gate is missing")
if "scripts/repair_blog_source.py" not in workflow or "scripts/test_blog_source_migrations.py" not in workflow:
    fail("guarded Blog D1 source migration gate is missing")

if "scripts/test_repository_hygiene.py" not in workflow:
    fail("repository hygiene gate is missing")

print("Operating runbook guard passed: one source of truth, human/API modes, authorization boundary, D1-driven locales, one generic publisher, and generic regression tests are documented.")

