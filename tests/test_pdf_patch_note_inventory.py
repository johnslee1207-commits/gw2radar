import shutil
from pathlib import Path
from uuid import uuid4

from gw2radar.kb_pdf.pdf_inventory import build_inventory, organize_pdf_sources


def test_pdf_patch_notes_are_inventoried_but_not_summarized_as_tier_one() -> None:
    repo_root = Path(".test_tmp") / f"pdf-patch-{uuid4().hex}"
    try:
        source_dir = repo_root / "docs" / "knowledge_base" / "official"
        source_root = repo_root / "docs" / "knowledge_base" / "_sources" / "pdf"
        source_dir.mkdir(parents=True)
        patch_name = "Game Update Notes_ May 12, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf"
        (source_dir / patch_name).write_bytes(b"%PDF fake patch note")

        organize_pdf_sources(source_dir, source_root)
        record = build_inventory(repo_root, source_root)[0]

        assert record.pdf_id == "pdf:patch:2026-05-12"
        assert record.category == "patch_note"
        assert record.priority == "P2"
        assert record.status == "pending"
        assert record.path.endswith(f"docs/knowledge_base/_sources/pdf/patch_notes/2026/{patch_name}")
    finally:
        shutil.rmtree(repo_root, ignore_errors=True)
