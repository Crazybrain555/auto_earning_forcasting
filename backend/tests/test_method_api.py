from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlencode

import pytest

from backend.app import method
from backend.app.main import app


def get(path: str, params: dict[str, str] | None = None):
    """Exercise the real FastAPI ASGI route without an optional HTTP client."""
    messages = []
    sent_request = False

    async def receive():
        nonlocal sent_request
        if sent_request:
            return {"type": "http.disconnect"}
        sent_request = True
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": urlencode(params or {}).encode(),
        "headers": [],
        "client": ("test-client", 1234),
        "server": ("test-server", 80),
        "root_path": "",
    }
    asyncio.run(app(scope, receive, send))
    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    headers = {key.decode(): value.decode() for key, value in start["headers"]}
    return start["status"], headers, body


@pytest.fixture
def live_skill(monkeypatch, tmp_path: Path) -> Path:
    skills_repo = tmp_path / "forecasting-skills"
    root = skills_repo / "technology-company-profit-forecasting"
    (root / "references").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "assets").mkdir()
    (root / "SKILL.md").write_text("# Live forecasting skill\nbody\n", encoding="utf-8")
    (root / "references" / "module-test.md").write_text(
        "# Test mechanism\nrule\n", encoding="utf-8"
    )
    (root / "scripts" / "private.txt").write_text("not public", encoding="utf-8")
    (root / "assets" / "method_system.json").write_text(
        json.dumps(
            {
                "schema_version": "forecast-method-system/v1",
                "method_id": "test-causal-value-system",
                "method_version": "9.0.0-test",
                "title": "Test method",
                "canonical_flow": ["evidence", "causal_graph", "valuation"],
                "judgment_boundary": {"allowed": ["thesis"], "prohibited": ["manual_weights"]},
                "optional_calibration": {"glob": "references/lens-*.md", "core_dependency": False},
                "stages": [
                    {
                        "no": 1,
                        "id": "contract",
                        "name": "Decision contract",
                        "purpose": "Freeze the boundary.",
                        "gates": ["dated"],
                        "files": ["SKILL.md", "references/mode-router-and-time-boundary.md"],
                    },
                    {
                        "no": 2,
                        "id": "operating_model",
                        "name": "Operating model",
                        "purpose": "Build equations.",
                        "gates": ["units"],
                        "files": ["references/module-*.md"],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(method, "SKILLS_REPO", skills_repo)
    return root


def test_skill_map_reports_existing_missing_and_globbed_responsibility_files(live_skill):
    result = method.skill_map()

    assert result["skill"] == "technology-company-profit-forecasting"
    assert result["root"] == str(live_skill)
    assert result["method_id"] == "test-causal-value-system"
    assert result["method_version"] == "9.0.0-test"
    assert len(result["stages"]) == 2

    scope_files = result["stages"][0]["files"]
    assert scope_files[0] == {
        "path": "SKILL.md",
        "exists": True,
        "lines": 2,
        "title": "Live forecasting skill",
    }
    assert any(
        item == {
            "path": "references/mode-router-and-time-boundary.md",
            "exists": False,
        }
        for item in scope_files
    )

    mechanism_files = result["stages"][1]["files"]
    assert {
        "path": "references/module-test.md",
        "exists": True,
        "lines": 2,
        "title": "Test mechanism",
    } in mechanism_files


def test_skill_file_reads_an_allowed_file_relative_to_the_live_skill(live_skill):
    assert method.skill_file("references/module-test.md") == (
        "references/module-test.md",
        "# Test mechanism\nrule\n",
    )


def test_skill_file_bounds_large_allowed_files_to_400000_characters(live_skill):
    large_file = live_skill / "references" / "large.json"
    large_file.write_text("x" * 400_001, encoding="utf-8")

    path, text = method.skill_file("references/large.json")

    assert path == "references/large.json"
    assert len(text) == 400_000


@pytest.mark.parametrize(
    "path",
    [
        "../outside.md",
        "references/../../outside.md",
        "scripts/private.txt",
        "references/missing.md",
    ],
)
def test_skill_file_rejects_traversal_disallowed_extensions_and_missing_files(
    live_skill, path
):
    outside = live_skill.parent / "outside.md"
    outside.write_text("secret", encoding="utf-8")

    assert method.skill_file(path) is None


def test_skill_file_rejects_a_symlink_that_escapes_the_live_skill(live_skill):
    outside = live_skill.parent / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    (live_skill / "references" / "escape.md").symlink_to(outside)

    assert method.skill_file("references/escape.md") is None


def test_method_skill_map_and_file_routes_expose_only_safe_content(live_skill):
    status, _, body = get("/api/method/skill-map")
    assert status == 200
    assert json.loads(body)["skill"] == "technology-company-profit-forecasting"

    status, headers, body = get(
        "/api/method/file", {"path": "references/module-test.md"}
    )
    assert status == 200
    assert headers["content-type"].startswith("text/plain")
    assert body.decode() == "# Test mechanism\nrule\n"


@pytest.mark.parametrize(
    "path",
    ["../outside.md", "scripts/private.txt", "references/missing.md"],
)
def test_method_file_route_returns_404_for_unsafe_or_missing_paths(live_skill, path):
    status, _, body = get("/api/method/file", {"path": path})

    assert status == 404
    assert json.loads(body) == {"detail": "file not found in live skill"}
