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


def test_claude_jobs_force_subagents_to_opus_mechanically():
    """The planning model (Fable/Opus per job) may vary, but execution
    subagents always run Opus via CLAUDE_CODE_SUBAGENT_MODEL — the top of the
    official subagent model resolution order. Injected per-engine through
    spec.env so the Mac backend and the AWS runner behave identically, with
    no routing prose reaching forecast prompts."""
    assert jobs.engines()["claude"]["env"]["CLAUDE_CODE_SUBAGENT_MODEL"] == "opus"
    codex_env = jobs.engines()["codex"].get("env") or {}
    assert "CLAUDE_CODE_SUBAGENT_MODEL" not in codex_env


def test_claude_engine_offers_fable_with_the_cli_recognized_id():
    """The dashboard can pick Fable for forecasts. The CLI only accepts the
    full model id (the `fable` alias is rejected), so the registry id must be
    `claude-fable-5` and compose_cmd must pass it through verbatim."""
    spec = jobs.engines()["claude"]
    ids = [m["id"] for m in spec["models"]]
    assert "claude-fable-5" in ids
    assert "fable" not in ids  # alias is not CLI-recognized; guard against a regression

    cmd = jobs.compose_cmd(spec, "forecast prompt", {"model": "claude-fable-5"})
    prompt_index = cmd.index("forecast prompt")
    assert cmd[prompt_index - 4 : prompt_index] == [
        "--model", "claude-fable-5", "--effort", "high",
    ]


@pytest.mark.parametrize(
    ("engine", "model", "expected_effort_args"),
    [
        ("claude", "sonnet", ["--effort", "high"]),
        ("claude", "claude-fable-5", ["--effort", "high"]),
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
