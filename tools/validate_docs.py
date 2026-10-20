#!/usr/bin/env python3
"""Check documentation bootstrap only; NOT GPU or algorithm validation."""
from pathlib import Path

root = Path(__file__).resolve().parent.parent
required = (
    "README.md", "AGENTS.md", "STATUS.md", "HANDOFF.md", "ROADMAP.md",
    "docs/DECISIONS.md", "docs/ARCHITECTURE.md",
    "docs/MEASUREMENT_CONTRACT.md", "docs/SOURCES_AND_LICENSES.md",
    "tasks/G0-01.md", ".github/pull_request_template.md",
)
for rel in required:
    p = root / rel
    assert p.is_file(), f"Missing: {rel}"
    data = p.read_text(encoding="utf-8")
    assert len(data) > 20, f"Empty or short: {rel}"
    assert data.endswith("\n"), f"Missing terminal newline: {rel}"
status = (root / "STATUS.md").read_text(encoding="utf-8")
handoff = (root / "HANDOFF.md").read_text(encoding="utf-8")
assert status.startswith("# STATUS"), "STATUS.md has an invalid heading"
assert handoff.startswith("# HANDOFF"), "HANDOFF.md has an invalid heading"
assert "Greenhound Online" in status and "Greenhound Online" in handoff
print(f"DOC PASS: {len(required)} required files and headings; no runtime tests were run")
