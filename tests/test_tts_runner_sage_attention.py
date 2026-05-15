"""Unit tests for SageAttention wiring in the WSL TTS runner."""

from __future__ import annotations

import importlib.util
import sys
import types
from collections.abc import Iterator
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.modules.setdefault("soundfile", types.ModuleType("soundfile"))
import tts_runner  # noqa: E402


@pytest.fixture(autouse=True)
def reset_sage_state() -> Iterator[None]:
    tts_runner._sage_enabled = False
    yield
    tts_runner._sage_enabled = False


def test_apply_sage_attention_patches_sdpa(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []

    torch_mod = types.ModuleType("torch")
    nn_mod = types.ModuleType("torch.nn")
    functional_mod = types.ModuleType("torch.nn.functional")

    def original_sdpa(*args, **kwargs):
        return ("sdpa", args, kwargs)

    functional_mod.scaled_dot_product_attention = original_sdpa
    nn_mod.functional = functional_mod
    torch_mod.nn = nn_mod

    sage_pkg = types.ModuleType("sageattention")
    sage_core = types.ModuleType("sageattention.core")

    def sage_kernel(query, key, value, **kwargs):
        calls.append(kwargs)
        return ("sage", query, key, value)

    sage_core.sageattn_qk_int8_pv_fp16_triton = sage_kernel
    sage_pkg.core = sage_core

    monkeypatch.setitem(sys.modules, "torch", torch_mod)
    monkeypatch.setitem(sys.modules, "torch.nn", nn_mod)
    monkeypatch.setitem(sys.modules, "torch.nn.functional", functional_mod)
    monkeypatch.setitem(sys.modules, "sageattention", sage_pkg)
    monkeypatch.setitem(sys.modules, "sageattention.core", sage_core)
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())

    assert tts_runner._apply_sage_attention(required=True) is True

    result = functional_mod.scaled_dot_product_attention("q", "k", "v", is_causal=True, scale=0.5)
    assert result == ("sage", "q", "k", "v")
    assert calls == [
        {
            "tensor_layout": "HND",
            "is_causal": True,
            "smooth_k": False,
            "sm_scale": 0.5,
        }
    ]

    fallback = functional_mod.scaled_dot_product_attention("q", "k", "v", attn_mask="mask")
    assert fallback[0] == "sdpa"


def test_apply_sage_attention_required_raises_without_kernel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    torch_mod = types.ModuleType("torch")
    nn_mod = types.ModuleType("torch.nn")
    functional_mod = types.ModuleType("torch.nn.functional")
    functional_mod.scaled_dot_product_attention = lambda *args, **kwargs: None
    nn_mod.functional = functional_mod
    torch_mod.nn = nn_mod

    monkeypatch.setitem(sys.modules, "torch", torch_mod)
    monkeypatch.setitem(sys.modules, "torch.nn", nn_mod)
    monkeypatch.setitem(sys.modules, "torch.nn.functional", functional_mod)
    monkeypatch.delitem(sys.modules, "sageattention", raising=False)
    monkeypatch.delitem(sys.modules, "sageattention.core", raising=False)
    monkeypatch.setattr(
        importlib.util,
        "find_spec",
        lambda name: object() if name == "torch" else None,
    )

    with pytest.raises(tts_runner.SageAttentionUnavailableError):
        tts_runner._apply_sage_attention(required=True)


def test_global_clone_prompt_matches_any_voice() -> None:
    prompts = {"__all__": object()}

    assert tts_runner._clone_prompt_for_voice("narrator_calm", prompts) is prompts["__all__"]


def test_generation_kwarg_fallback_retries_without_controls() -> None:
    calls: list[dict] = []

    def method(**kwargs):
        calls.append(kwargs)
        if "temperature" in kwargs:
            raise TypeError("unexpected keyword argument 'temperature'")
        return "ok"

    result = tts_runner._call_with_generation_kwargs(
        method,
        {
            "text": "hello",
            "temperature": 1.0,
            "top_p": 0.8,
        },
    )

    assert result == "ok"
    assert calls == [
        {"text": "hello", "temperature": 1.0, "top_p": 0.8},
        {"text": "hello"},
    ]
