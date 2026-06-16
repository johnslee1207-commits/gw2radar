from pathlib import Path


def test_security_modules_do_not_add_forbidden_capabilities() -> None:
    forbidden = ["proxy_pool", "ip_rotation", "automated_trading", "gameplay_automation"]
    for path in Path("src/gw2radar/security").rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        assert not any(term in text for term in forbidden), path
