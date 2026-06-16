import csv
import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from gw2radar.kb_pdf.pdf_classifier import classify_pdf, extract_patch_date


@dataclass(frozen=True)
class PdfSourceRecord:
    pdf_id: str
    file_name: str
    path: str
    size_bytes: int
    category: str
    year: int | None
    priority: str
    status: str
    sha256: str


CSV_FIELDS = [
    "pdf_id",
    "file_name",
    "path",
    "size_bytes",
    "category",
    "year",
    "priority",
    "status",
    "sha256",
]


def discover_pdf_files(*roots: Path) -> list[Path]:
    files: dict[str, Path] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.pdf"):
            files[str(path.resolve()).lower()] = path
    return sorted(files.values(), key=lambda item: item.name.lower())


def organize_pdf_sources(source_dir: Path, source_root: Path) -> list[Path]:
    moved: list[Path] = []
    for pdf_path in discover_pdf_files(source_dir):
        classification = classify_pdf(pdf_path.name)
        target_dir = source_root / classification.target_relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / pdf_path.name
        if pdf_path.resolve() == target_path.resolve():
            moved.append(target_path)
            continue
        if target_path.exists():
            pdf_path.unlink()
        else:
            shutil.move(str(pdf_path), str(target_path))
        moved.append(target_path)
    return sorted(moved, key=lambda item: item.name.lower())


def build_inventory(repo_root: Path, source_root: Path) -> list[PdfSourceRecord]:
    records: list[PdfSourceRecord] = []
    for pdf_path in discover_pdf_files(source_root):
        classification = classify_pdf(pdf_path.name)
        records.append(
            PdfSourceRecord(
                pdf_id=build_pdf_id(pdf_path.name, classification.category),
                file_name=pdf_path.name,
                path=pdf_path.relative_to(repo_root).as_posix(),
                size_bytes=pdf_path.stat().st_size,
                category=classification.category,
                year=classification.year,
                priority=classification.priority,
                status=classification.status,
                sha256=sha256_file(pdf_path),
            )
        )
    return records


def write_inventory_csv(records: list[PdfSourceRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for record in records:
            row = record.__dict__.copy()
            row["year"] = "" if record.year is None else str(record.year)
            writer.writerow(row)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_pdf_id(file_name: str, category: str) -> str:
    if category == "patch_note":
        patch_date = extract_patch_date(file_name)
        if patch_date:
            return f"pdf:patch:{patch_date}"
    if category == "official_api_endpoint":
        endpoint = file_name.removeprefix("API_2_").split(" - ", 1)[0].lower()
        return f"pdf:api_endpoint:{_slug(endpoint)}"
    if file_name.startswith("API_2 -"):
        return "pdf:api:v2"
    if file_name.startswith("API_Main"):
        return "pdf:api:main"
    if file_name.startswith("API_Best practices"):
        return "pdf:api:best_practices"
    if file_name.startswith("API_API key"):
        return "pdf:api:key"
    if file_name.startswith("API_2_tokeninfo"):
        return "pdf:api:tokeninfo"
    return f"pdf:{category}:{_slug(Path(file_name).stem)}"


def _slug(value: str) -> str:
    return "_".join(part for part in "".join(ch.lower() if ch.isalnum() else "_" for ch in value).split("_") if part)
