from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_workspace_hygiene_ignores_local_outputs() -> None:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    required_patterns = [
        "desktop.ini",
        "Thumbs.db",
        "agent_execution_pack*.zip",
        "docs/knowledge_base/_sources/",
        "src/gw2radar/reports/artifacts/",
        "*.db",
        "*.sqlite",
    ]

    missing = [pattern for pattern in required_patterns if pattern not in gitignore]
    assert not missing


def test_workspace_hygiene_documents_promotion_boundaries() -> None:
    hygiene = (ROOT / "docs" / "WORKSPACE_HYGIENE.md").read_text(encoding="utf-8")

    required_phrases = [
        "docs/analysis/*.md",
        "raw downloaded source files",
        "generated local delivery artifacts",
        "Do not commit raw API keys",
        "private account payloads",
    ]

    missing = [phrase for phrase in required_phrases if phrase not in hygiene]
    assert not missing
