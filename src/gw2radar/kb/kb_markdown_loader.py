from pathlib import Path

from sqlalchemy.orm import Session

from gw2radar.kb.kb_models import KnowledgeArticleInput
from gw2radar.kb.kb_repository import create_article


def load_markdown_article(session: Session, path: Path) -> object:
    resolved = path.resolve()
    if resolved.suffix.lower() != ".md":
        raise ValueError("Knowledge Base loader only accepts Markdown files.")
    if not resolved.exists() or not resolved.is_file():
        raise ValueError("Knowledge Base Markdown file not found.")
    text = resolved.read_text(encoding="utf-8")
    metadata, body = _parse_front_matter(text)
    article = KnowledgeArticleInput(
        title=_required(metadata, "title"),
        domain=_required(metadata, "domain"),
        content_type=_required(metadata, "content_type"),
        summary=_required(metadata, "summary"),
        body_markdown=body.strip(),
        source_refs=_csv(metadata.get("source_refs", "")),
        linked_entities=_csv(metadata.get("linked_entities", "")),
        linked_relations=_csv(metadata.get("linked_relations", "")),
        linked_actions=_csv(metadata.get("linked_actions", "")),
        confidence=float(metadata.get("confidence", "0.6")),
        review_status=metadata.get("review_status", "draft"),
    )
    return create_article(session, article)


def _parse_front_matter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("Knowledge Base Markdown must start with front matter.")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("Knowledge Base Markdown front matter is not closed.")
    raw_meta = text[4:end]
    body = text[end + 5 :]
    metadata: dict[str, str] = {}
    for line in raw_meta.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise ValueError(f"Invalid front matter line: {line}")
        key, value = stripped.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata, body


def _required(metadata: dict[str, str], key: str) -> str:
    value = metadata.get(key, "").strip()
    if not value:
        raise ValueError(f"Missing required Knowledge Base metadata: {key}")
    return value


def _csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]
