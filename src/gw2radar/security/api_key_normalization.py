ZERO_WIDTH_CHARS = {"\ufeff", "\u200b", "\u200c", "\u200d"}


def normalize_api_key(api_key: str) -> str:
    """Normalize pasted GW2 API keys without changing their real token content."""
    return "".join(ch for ch in api_key.strip() if not ch.isspace() and ch not in ZERO_WIDTH_CHARS)
