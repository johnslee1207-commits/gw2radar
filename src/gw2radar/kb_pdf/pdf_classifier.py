import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class PdfClassification:
    category: str
    year: int | None
    priority: str
    status: str
    target_relative_dir: str


def classify_pdf(file_name: str) -> PdfClassification:
    name = Path(file_name).name
    lower = name.lower()
    year = extract_year(name)

    if "api_2_tokeninfo" in lower:
        return PdfClassification("api_permission", year, "P0", "pending", "official_api")
    if "api_api key" in lower:
        return PdfClassification("api_key", year, "P0", "pending", "official_api")
    if "api_best practices" in lower:
        return PdfClassification("api_governance", year, "P0", "pending", "official_api")
    if lower.startswith("api_2_"):
        return PdfClassification("official_api_endpoint", year, "P1", "pending", "official_api/endpoints")
    if "api_main" in lower or re.match(r"api_2\s+-", lower):
        return PdfClassification("official_api", year, "P0", "pending", "official_api")
    if "arenanet" in lower:
        return PdfClassification("arenanet_policy", year, "P0", "pending", "arenanet")
    if "game update notes" in lower or "game release notes" in lower or "release notes" in lower:
        if year and year >= 2024:
            return PdfClassification("patch_note", year, "P2", "pending", f"patch_notes/{year}")
        return PdfClassification("patch_note", year, "P3", "pending", "patch_notes/archive_2017_2023")
    if "gallant longbow skin" in lower or "api talk" in lower:
        return PdfClassification("low_priority", year, "P4", "archived", "low_priority")
    if (
        "guild wars 2 wiki" in lower
        or lower.startswith("help_")
        or "recent changes" in lower
        or "quick access links" in lower
    ):
        return PdfClassification("wiki_meta", year, "P3", "pending", "wiki_meta")
    return PdfClassification("low_priority", year, "P4", "archived", "low_priority")


def extract_year(file_name: str) -> int | None:
    match = re.search(r"\b(20\d{2}|2017|2018|2019)\b", file_name)
    if match:
        return int(match.group(1))
    return None


def extract_patch_date(file_name: str) -> str | None:
    iso_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", file_name)
    if iso_match:
        return iso_match.group(1)

    month_match = re.search(
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+(\d{1,2}),\s+(20\d{2}|2017|2018|2019)\b",
        file_name,
        flags=re.IGNORECASE,
    )
    if not month_match:
        return None
    parsed = datetime.strptime(" ".join(month_match.groups()), "%B %d %Y")
    return parsed.date().isoformat()
