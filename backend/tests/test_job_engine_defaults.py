from __future__ import annotations

import pytest

from backend.app import jobs


@pytest.mark.parametrize(
    ("engine", "model_args", "effort_args"),
    [
        ("claude", ["--model", "opus"], ["--effort", "max"]),
        (
            "codex",
            ["-m", "gpt-5.6-sol"],
            ["-c", 'model_reasoning_effort="xhigh"'],
        ),
    ],
)
def test_compose_cmd_uses_each_engine_default_model_and_effort(
    engine, model_args, effort_args
):
    cmd = jobs.compose_cmd(jobs.engines()[engine], "forecast prompt", {})

    prompt_index = cmd.index("forecast prompt")
    assert cmd[prompt_index - 4 : prompt_index] == model_args + effort_args


@pytest.mark.parametrize(
    ("engine", "params", "model_args", "effort_args"),
    [
        (
            "claude",
            {"model": "sonnet", "effort": "medium"},
            ["--model", "sonnet"],
            ["--effort", "medium"],
        ),
        (
            "codex",
            {"model": "gpt-5.6-terra", "effort": "ultra"},
            ["-m", "gpt-5.6-terra"],
            ["-c", 'model_reasoning_effort="ultra"'],
        ),
    ],
)
def test_compose_cmd_explicit_model_and_effort_override_engine_defaults(
    engine, params, model_args, effort_args
):
    cmd = jobs.compose_cmd(jobs.engines()[engine], "forecast prompt", params)

    prompt_index = cmd.index("forecast prompt")
    assert cmd[prompt_index - 4 : prompt_index] == model_args + effort_args


@pytest.mark.parametrize(
    ("engine", "model", "expected_effort_args"),
    [
        ("claude", "sonnet", ["--effort", "high"]),
        ("codex", "gpt-5.6-terra", ["-c", 'model_reasoning_effort="high"']),
    ],
)
def test_explicit_model_uses_that_models_default_effort(
    engine, model, expected_effort_args
):
    cmd = jobs.compose_cmd(
        jobs.engines()[engine], "forecast prompt", {"model": model}
    )

    prompt_index = cmd.index("forecast prompt")
    assert cmd[prompt_index - 2 : prompt_index] == expected_effort_args


@pytest.mark.parametrize(
    ("engine", "effort", "expected_args"),
    [
        ("claude", "low", ["--model", "opus", "--effort", "low"]),
        (
            "codex",
            "medium",
            ["-m", "gpt-5.6-sol", "-c", 'model_reasoning_effort="medium"'],
        ),
    ],
)
def test_explicit_effort_overrides_default_for_the_default_model(
    engine, effort, expected_args
):
    cmd = jobs.compose_cmd(
        jobs.engines()[engine], "forecast prompt", {"effort": effort}
    )

    prompt_index = cmd.index("forecast prompt")
    assert cmd[prompt_index - 4 : prompt_index] == expected_args


def test_engine_default_effort_is_the_fallback_when_model_has_none():
    spec = {
        "cmd": ["agent", "{prompt}"],
        "default_model": "primary",
        "default_effort": "high",
        "model_args": ["--model", "{model}"],
        "effort_args": ["--effort", "{effort}"],
        "models": [{"id": "primary", "efforts": ["low", "high"]}],
    }

    assert jobs.compose_cmd(spec, "forecast prompt", {}) == [
        "agent",
        "--model",
        "primary",
        "--effort",
        "high",
        "forecast prompt",
    ]
