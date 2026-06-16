import csv
import shutil
from pathlib import Path
from uuid import uuid4

from gw2radar.kb_pdf.pdf_inventory import build_inventory, organize_pdf_sources, write_inventory_csv


def test_pdf_inventory_moves_sources_and_writes_hashes() -> None:
    repo_root = Path(".test_tmp") / f"pdf-inventory-{uuid4().hex}"
    try:
        source_dir = repo_root / "docs" / "knowledge_base" / "official"
        source_root = repo_root / "docs" / "knowledge_base" / "_sources" / "pdf"
        source_dir.mkdir(parents=True)
        (source_dir / "API_2_account - Guild Wars 2 Wiki (GW2W).pdf").write_bytes(b"%PDF fake account")
        (source_dir / "Game Update Notes_ June 2, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf").write_bytes(
            b"%PDF fake patch"
        )

        organize_pdf_sources(source_dir, source_root)
        records = build_inventory(repo_root, source_root)
        output_path = repo_root / "data" / "kb" / "pdf_inventory.csv"
        write_inventory_csv(records, output_path)

        rows = list(csv.DictReader(output_path.open(encoding="utf-8")))
        assert len(rows) == 2
        assert {row["category"] for row in rows} == {"official_api_endpoint", "patch_note"}
        assert all(row["sha256"] for row in rows)
        assert (source_root / "official_api" / "endpoints" / "API_2_account - Guild Wars 2 Wiki (GW2W).pdf").exists()
        assert (
            source_root
            / "patch_notes"
            / "2026"
            / "Game Update Notes_ June 2, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf"
        ).exists()
    finally:
        shutil.rmtree(repo_root, ignore_errors=True)
