from __future__ import annotations

from pathlib import Path

import tomllib


def _optional_dependencies() -> dict[str, list[str]]:
    metadata = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    return metadata["project"]["optional-dependencies"]


def test_tts_extras_pin_heavy_runtime_dependencies() -> None:
    optional_dependencies = _optional_dependencies()

    assert "qwen-tts==0.1.1" in optional_dependencies["tts"]
    assert "torch==2.7.1" in optional_dependencies["tts"]
    assert "qwen-tts==0.1.1" in optional_dependencies["tts-sage"]
    assert "torch==2.7.1" in optional_dependencies["tts-sage"]
    assert "sageattention==1.0.6" in optional_dependencies["tts-sage"]


def test_optional_dependencies_do_not_use_direct_git_references() -> None:
    optional_dependencies = _optional_dependencies()

    dependencies = [
        dependency
        for extra_dependencies in optional_dependencies.values()
        for dependency in extra_dependencies
    ]

    assert all("git+" not in dependency for dependency in dependencies)
    assert all(" @ " not in dependency for dependency in dependencies)
