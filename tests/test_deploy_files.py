"""The image and compose files of `PHASE_3.md` 3.9 (k) 6, 7 (DECISIONS.md #416, #417, #424), read as
text and YAML: nothing is built and Docker is never called."""

import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
STORE_MOUNT = "store:/app/data/store"
KEY_NAMES = ("APIFY_TOKEN", "OPENAI_API_KEY")
DIGEST = re.compile(r"@sha256:[0-9a-f]{64}(\s|,|$)")


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load((ROOT / "compose.yaml").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def dockerfile() -> str:
    return (ROOT / "Dockerfile").read_text(encoding="utf-8")


def test_every_published_port_is_on_127_0_0_1_only(compose: dict) -> None:
    published = [
        str(port) for service in compose["services"].values() for port in service.get("ports", [])
    ]
    assert published == ["127.0.0.1:8000:8000"]


def test_the_site_holds_no_key(compose: dict) -> None:
    site = compose["services"]["site"]
    assert "env_file" not in site
    environment = site.get("environment", {})
    names = environment if isinstance(environment, list) else list(environment)
    assert not any(key in str(name) for name in names for key in KEY_NAMES)


def test_the_site_runs_serve_store_inside_the_container(compose: dict, dockerfile: str) -> None:
    command = ["python", "-m", "tlv_hunter.jobs.serve", "--store", "--host", "0.0.0.0"]
    assert compose["services"]["site"]["command"] == command
    cmd = 'CMD ["python", "-m", "tlv_hunter.jobs.serve", "--store", "--host", "0.0.0.0"]'
    assert cmd in dockerfile


def test_both_services_mount_the_one_volume_at_the_store_root(compose: dict) -> None:
    for name in ("site", "jobs"):
        assert STORE_MOUNT in compose["services"][name]["volumes"], name
    assert compose["volumes"]["store"]["name"] == "tlv-hunter-store"
    # Every other mount of `jobs` is a folder of plain files, never the store.
    others = [v for v in compose["services"]["jobs"]["volumes"] if v != STORE_MOUNT]
    assert others and all(not v.split(":")[1].startswith("/app/data/store/") for v in others)
    assert all(v.split(":")[1] != "/app/data/store" for v in others)


def test_jobs_has_a_profile_the_keys_and_never_pulls(compose: dict) -> None:
    jobs = compose["services"]["jobs"]
    assert jobs["profiles"] == ["jobs"]
    # The two job keys by name, from .env (#452): never the whole file, which holds the bot's token.
    assert "env_file" not in jobs
    assert jobs["environment"] == {name: f"${{{name}:-}}" for name in KEY_NAMES}
    assert jobs["pull_policy"] == "never"
    assert jobs["image"] == compose["services"]["site"]["image"]


def test_the_bot_alone_gets_the_token_and_starts_only_by_name(compose: dict) -> None:
    bot = compose["services"]["bot"]
    assert bot["profiles"] == ["bot"] and bot["pull_policy"] == "never"
    assert bot["image"] == compose["services"]["site"]["image"]
    assert bot["command"] == ["python", "-m", "tlv_hunter.jobs.bot"]
    assert bot["environment"] == {
        "TELEGRAM_BOT_TOKEN": "${TELEGRAM_BOT_TOKEN:-}",
        "SITE_URL": "${SITE_URL:-}",
    }
    assert bot["volumes"] == [STORE_MOUNT] and "ports" not in bot
    for name, service in compose["services"].items():
        if name != "bot":
            assert "TELEGRAM_BOT_TOKEN" not in yaml.safe_dump(service), name


def test_every_base_image_carries_a_digest(dockerfile: str) -> None:
    froms = [line for line in dockerfile.splitlines() if line.startswith("FROM ")]
    assert len(froms) == 2  # two stages (#258)
    for line in froms:
        assert DIGEST.search(line), line
    mounted = [line for line in dockerfile.splitlines() if "--mount=from=" in line]
    assert len(mounted) == 1 and DIGEST.search(mounted[0])


def test_the_image_installs_no_dev_group_and_leaves_no_uv(dockerfile: str) -> None:
    assert "UV_NO_DEV=1" in dockerfile and "uv sync --locked" in dockerfile
    assert "COPY --from=ghcr.io/astral-sh/uv" not in dockerfile
    assert "USER app" in dockerfile


def test_the_build_context_is_an_allow_list() -> None:
    lines = [
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    assert lines[0] == "*"
    allowed = {line[1:].rstrip("/") for line in lines if line.startswith("!")}
    assert allowed == {
        "tlv_hunter",
        "config",
        "reference",
        "frontend",
        "pyproject.toml",
        "uv.lock",
        ".python-version",
    }
    for never in ("data", ".env", "scratch", "docs", ".git", "CLAUDE.md"):
        assert not any(a == never or a.startswith(never + "/") for a in allowed), never
    assert {"frontend/node_modules", "frontend/dist"} <= set(lines)
