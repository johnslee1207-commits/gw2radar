from pathlib import Path


BENCHMARK_ROOT = Path("docs/benchmark")

REQUIRED_DOCS = [
    "gw2efficiency_benchmark.md",
    "wowhead_planner_benchmark.md",
    "path_of_building_benchmark.md",
    "snowcrows_benchmark.md",
    "metabattle_benchmark.md",
    "kg_rag_knowledge_management_benchmark.md",
    "benchmark_matrix.md",
]

REQUIRED_SECTIONS = [
    "## Reference Links",
    "## Core Features",
    "## Data Model Signals",
    "## Strengths",
    "## Weaknesses For GW2Radar Positioning",
    "## What GW2Radar Should Copy",
    "## What GW2Radar Should Avoid",
    "## Differentiation",
]

FORBIDDEN_COPY_MARKERS = [
    "full article copied",
    "verbatim transcript",
    "entire guide text",
    "copied full guide",
]


def test_benchmark_pack_contains_required_documents() -> None:
    assert all((BENCHMARK_ROOT / name).exists() for name in REQUIRED_DOCS)


def test_benchmark_documents_are_structured_and_linked() -> None:
    for name in REQUIRED_DOCS:
        text = (BENCHMARK_ROOT / name).read_text(encoding="utf-8")
        assert "https://" in text
        assert "GW2Radar" in text
        if name != "benchmark_matrix.md":
            for section in REQUIRED_SECTIONS:
                assert section in text, f"{name} missing {section}"


def test_benchmark_pack_preserves_summary_only_boundary() -> None:
    combined = "\n".join((BENCHMARK_ROOT / name).read_text(encoding="utf-8") for name in REQUIRED_DOCS)
    lowered = combined.lower()

    assert "do not copy third-party guide bodies" in lowered
    assert "RAG may explain reviewed evidence-backed results".lower() in lowered
    assert all(marker not in lowered for marker in FORBIDDEN_COPY_MARKERS)
