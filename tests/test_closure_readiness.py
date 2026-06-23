from harness.closure_readiness import build_closure_readiness, render_markdown


def test_closure_readiness_has_no_blocking_tasks() -> None:
    readiness = build_closure_readiness()

    assert readiness["schema_version"] == "gw2radar.mvp_closure_readiness.v1"
    assert readiness["status"] == "ready_to_close_mvp_stage"
    assert readiness["blocking_task_count"] == 0
    assert readiness["optional_task_count"] == 3


def test_closure_readiness_preserves_three_optional_tracks() -> None:
    readiness = build_closure_readiness()
    task_ids = {task["task_id"] for task in readiness["optional_post_mvp_tasks"]}

    assert task_ids == {
        "reviewed_content_depth",
        "optional_live_api_smoke_documentation",
        "ui_visual_polish",
    }
    assert all(not task["blocking_mvp"] for task in readiness["optional_post_mvp_tasks"])


def test_closure_readiness_markdown_sections() -> None:
    markdown = render_markdown(build_closure_readiness())

    assert "# MVP Closure Readiness" in markdown
    assert "Blocking task count: 0" in markdown
    assert "Optional post-MVP task count: 3" in markdown
    assert "## Required Closeout Commands" in markdown
