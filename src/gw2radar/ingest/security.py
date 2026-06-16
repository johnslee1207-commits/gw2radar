def mask_api_key(api_key: str | None) -> str | None:
    if api_key is None:
        return None
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"
