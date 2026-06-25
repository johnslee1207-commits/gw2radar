from gw2radar.player_os.intent.intent_templates import get_intent_template, list_intent_templates
from gw2radar.player_os.orchestration.player_os_orchestrator import start_intent, start_template


def test_templates_cover_player_os_domains() -> None:
    templates = list_intent_templates()
    domains = {template.domain for template in templates}

    assert {"returner", "legendary", "build_fit", "account", "market"}.issubset(domains)
    assert get_intent_template("legendary.aurora_cheap_path") is not None
    assert all(template.required_permissions for template in templates)


def test_template_start_builds_workflow_plan_and_report() -> None:
    result = start_template("legendary.aurora_cheap_path")

    assert result.intent.intent_type == "legendary"
    assert result.workflow.workflow_type == "legendary_wizard"
    assert result.plan.top_actions
    assert result.report_preview.sections
    assert result.governance["status"] == "ready"


def test_start_now_intent_builds_now_workflow() -> None:
    result = start_intent("What should I do now?")

    assert result.intent.intent_type == "what_should_i_do_now"
    assert result.workflow.workflow_type == "what_should_i_do_now_wizard"
    assert result.plan.title == "What Should I Do Now?"
    assert all(action.safety_boundary == "advisory_manual_action_only" for action in result.plan.top_actions)
