from nico.config.prompts import PromptTemplates


def test_prompt_templates_defaults() -> None:
    prompts = PromptTemplates()
    assert "NICO" in prompts.system_prompt
    assert len(prompts.system_prompt) > 50


def test_prompt_templates_has_confirmation() -> None:
    prompts = PromptTemplates()
    assert "confirmation" in prompts.confirmation_prompt.lower()


def test_prompt_templates_has_tool_unavailable() -> None:
    prompts = PromptTemplates()
    assert "don't have access" in prompts.tool_unavailable_prompt
