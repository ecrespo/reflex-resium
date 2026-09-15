"""Reflex plugin that serves Cesium's static assets from your own app.

Cesium loads Web Workers, textures, ThirdParty wasm and widget images at
runtime from ``CESIUM_BASE_URL``. Without this plugin reflex-resium points that
URL at the jsDelivr CDN (zero configuration, needs internet access). With the
plugin the assets are served from ``node_modules/cesium/Build/Cesium``:

* ``reflex run`` (dev): a Vite middleware serves ``/<frontend_path>/cesium/*``.
* ``reflex export`` / prod: the folder is copied into the client build as ``cesium/``.

Usage in ``rxconfig.py``::

    import reflex as rx
    from reflex_resium import ResiumPlugin

    config = rx.Config(
        app_name="my_app",
        plugins=[ResiumPlugin(ion_access_token="...")],
    )
"""

from __future__ import annotations

import dataclasses
import json
import os

from reflex.plugins.base import Plugin

from .constants import CESIUM_CDN_BASE_URL, CESIUM_LOCAL_ASSETS_PATH, ION_TOKEN_ENV_VAR

__all__ = ["ResiumPlugin", "get_cesium_base_url", "get_ion_access_token"]

_VITE_MARKER = "reflexResiumCesiumAssets"

_VITE_PLUGIN_SOURCE = r"""
// --- reflex-resium: serve and bundle Cesium static assets -----------------
import { createReadStream as __resiumCreateReadStream, existsSync as __resiumExists, statSync as __resiumStat, cpSync as __resiumCp } from "fs";
import { join as __resiumJoin, extname as __resiumExtname, resolve as __resiumResolve, sep as __resiumSep } from "path";
function reflexResiumCesiumAssets(prefix, dest) {
  const root = __resiumResolve(fileURLToPath(new URL("./node_modules/cesium/Build/Cesium", import.meta.url)));
  const types = { ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json", ".css": "text/css", ".wasm": "application/wasm", ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".xml": "application/xml", ".glb": "model/gltf-binary", ".ktx2": "image/ktx2", ".woff": "font/woff", ".ttf": "font/ttf" };
  const middleware = (req, res, next) => {
    const url = decodeURIComponent((req.url || "").split("?")[0]);
    if (!url.startsWith(prefix)) return next();
    const file = __resiumResolve(__resiumJoin(root, url.slice(prefix.length)));
    if (!file.startsWith(root + __resiumSep) || !__resiumExists(file) || !__resiumStat(file).isFile()) return next();
    res.setHeader("Content-Type", types[__resiumExtname(file).toLowerCase()] || "application/octet-stream");
    res.setHeader("Cache-Control", "public, max-age=3600");
    __resiumCreateReadStream(file).pipe(res);
  };
  return {
    name: "reflex-resium-cesium-assets",
    configureServer(server) { server.middlewares.use(middleware); },
    configurePreviewServer(server) { server.middlewares.use(middleware); },
    writeBundle(options) {
      if (this.environment && this.environment.name && this.environment.name !== "client") return;
      if (!options.dir || !__resiumExists(root)) return;
      for (const folder of ["Workers", "ThirdParty", "Assets", "Widgets"]) {
        const from = __resiumJoin(root, folder);
        if (__resiumExists(from)) __resiumCp(from, __resiumJoin(options.dir, dest, folder), { recursive: true });
      }
    },
  };
}
// --------------------------------------------------------------------------
"""


def _inject_vite_plugin(prefix: str):
    define_anchor = "export default defineConfig"
    plugins_anchor = "alwaysUseReactDomServerNode(),"

    def modify(content: str) -> str:
        if _VITE_MARKER in content:
            return content
        if define_anchor not in content or plugins_anchor not in content:
            msg = (
                "ResiumPlugin cannot patch vite.config.js: expected anchors were not "
                "found. Use ResiumPlugin(serve_assets=False) and set base_url instead."
            )
            raise RuntimeError(msg)
        # Imports must stay at the top of an ES module.
        return content.replace(define_anchor, _VITE_PLUGIN_SOURCE + "\n" + define_anchor, 1).replace(
            plugins_anchor,
            f"{_VITE_MARKER}({json.dumps(prefix)}, {json.dumps(CESIUM_LOCAL_ASSETS_PATH.strip('/'))}),\n    {plugins_anchor}",
            1,
        )

    return modify


def _hoist_imports(content: str) -> str:
    """Move ``import`` lines injected mid-file to the top of vite.config.js."""
    lines = content.splitlines()
    injected = [ln for ln in lines if ln.startswith("import ") and "__resium" in ln]
    rest = [ln for ln in lines if ln not in injected]
    return "\n".join(injected + rest) + "\n"


@dataclasses.dataclass
class ResiumPlugin(Plugin):
    """Serve Cesium assets locally and configure Cesium globally.

    Attributes:
        serve_assets: Serve/copy ``cesium/Build/Cesium`` from node_modules.
        base_url: Explicit ``CESIUM_BASE_URL`` (e.g. your own CDN). Overrides
            ``serve_assets`` for the runtime URL.
        ion_access_token: Cesium ion token (falls back to the
            ``CESIUM_ION_ACCESS_TOKEN`` environment variable).
    """

    serve_assets: bool = True
    base_url: str | None = None
    ion_access_token: str | None = None

    def pre_compile(self, **context):
        """Patch vite.config.js with the asset middleware/copy plugin.

        Args:
            context: The pre-compile context.
        """
        if not self.serve_assets:
            return
        from reflex.config import get_config

        prefix = get_config().prepend_frontend_path("/" + CESIUM_LOCAL_ASSETS_PATH)
        inject = _inject_vite_plugin(prefix)
        context["add_modify_task"]("vite.config.js", lambda c: _hoist_imports(inject(c)))


def _configured_plugin() -> ResiumPlugin | None:
    try:
        from reflex.config import get_config

        plugins = [p for p in get_config().plugins if isinstance(p, ResiumPlugin)]
    except Exception:  # noqa: BLE001 - config may be unavailable (tests, scripts)
        return None
    return plugins[0] if plugins else None


def get_cesium_base_url() -> str:
    """Resolve the runtime ``CESIUM_BASE_URL``.

    Order: ``ResiumPlugin.base_url`` > locally served assets (plugin) >
    ``CESIUM_BASE_URL`` environment variable > jsDelivr CDN.

    Returns:
        The URL (always ending with ``/``).
    """
    plugin = _configured_plugin()
    url: str | None = None
    if plugin is not None:
        if plugin.base_url:
            url = plugin.base_url
        elif plugin.serve_assets:
            from reflex.config import get_config

            url = get_config().prepend_frontend_path("/" + CESIUM_LOCAL_ASSETS_PATH)
    url = url or os.environ.get("CESIUM_BASE_URL") or CESIUM_CDN_BASE_URL
    return url if url.endswith("/") else url + "/"


def get_ion_access_token() -> str | None:
    """Resolve the Cesium ion access token (plugin, then environment variable).

    Returns:
        The token or ``None`` to keep Cesium's default.
    """
    plugin = _configured_plugin()
    if plugin is not None and plugin.ion_access_token:
        return plugin.ion_access_token
    return os.environ.get(ION_TOKEN_ENV_VAR) or None
