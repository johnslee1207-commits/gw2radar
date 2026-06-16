import json
from importlib.resources import files
from typing import Any


FIXTURE_PACKAGE = "gw2radar.fixtures"


def load_fixture(name: str) -> Any:
    resource = files(FIXTURE_PACKAGE).joinpath(name)
    return json.loads(resource.read_text(encoding="utf-8"))


def load_mock_bundle() -> dict[str, Any]:
    return {
        "account": load_fixture("mock_account.json"),
        "goal": load_fixture("mock_goal_aurora.json"),
        "items": load_fixture("mock_items.json"),
        "tasks": load_fixture("mock_tasks.json"),
    }
