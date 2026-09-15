"""ResiumPlugin: vite.config.js patching and runtime configuration."""

from __future__ import annotations

import pytest

from reflex_resium.constants import CESIUM_CDN_BASE_URL, ION_TOKEN_ENV_VAR
from reflex_resium.plugin import _hoist_imports, _inject_vite_plugin, get_cesium_base_url, get_ion_access_token

VITE_CONFIG = """import { fileURLToPath, URL } from "url";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [
    alwaysUseReactDomServerNode(),
  ],
});
"""


def _patch(content: str) -> str:
    return _hoist_imports(_inject_vite_plugin("/cesium/")(content))


def test_vite_config_is_patched_with_imports_first():
    patched = _patch(VITE_CONFIG)
    lines = patched.splitlines()
    assert all(line.startswith("import ") for line in lines[:4])
    assert 'reflexResiumCesiumAssets("/cesium/", "cesium"),' in patched
    assert patched.index("function reflexResiumCesiumAssets") < patched.index("export default defineConfig")


def test_vite_patch_is_idempotent():
    once = _patch(VITE_CONFIG)
    assert _patch(once) == once


def test_vite_patch_fails_loudly_without_anchors():
    with pytest.raises(RuntimeError, match="serve_assets=False"):
        _inject_vite_plugin("/cesium/")("export const x = 1;\n")


def test_base_url_defaults_to_cdn(monkeypatch):
    monkeypatch.delenv("CESIUM_BASE_URL", raising=False)
    assert get_cesium_base_url() == CESIUM_CDN_BASE_URL


def test_base_url_from_environment_gets_trailing_slash(monkeypatch):
    monkeypatch.setenv("CESIUM_BASE_URL", "https://example.com/cesium")
    assert get_cesium_base_url() == "https://example.com/cesium/"


def test_ion_token_from_environment(monkeypatch):
    monkeypatch.delenv(ION_TOKEN_ENV_VAR, raising=False)
    assert get_ion_access_token() is None
    monkeypatch.setenv(ION_TOKEN_ENV_VAR, "token-123")
    assert get_ion_access_token() == "token-123"
