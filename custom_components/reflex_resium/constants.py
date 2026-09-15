"""Pinned versions and shared constants for reflex-resium."""

from __future__ import annotations

#: Version of the ``resium`` npm package wrapped by this library.
RESIUM_VERSION = "1.26.0"

#: Version of the ``cesium`` npm package (peer dependency of resium).
CESIUM_VERSION = "1.145.0"

#: npm specifier for resium.
RESIUM_LIBRARY = f"resium@{RESIUM_VERSION}"

#: npm specifier for cesium.
CESIUM_LIBRARY = f"cesium@{CESIUM_VERSION}"

#: Widgets stylesheet shipped inside the cesium npm package (Viewer UI).
CESIUM_WIDGETS_CSS = "cesium/Build/Cesium/Widgets/widgets.css"

#: Default location of Cesium's static assets (Workers, Assets, ThirdParty,
#: Widgets) when the :class:`~reflex_resium.plugin.ResiumPlugin` is not used.
CESIUM_CDN_BASE_URL = f"https://cdn.jsdelivr.net/npm/cesium@{CESIUM_VERSION}/Build/Cesium/"

#: Path (relative to the frontend root) where ResiumPlugin serves Cesium assets.
CESIUM_LOCAL_ASSETS_PATH = "cesium/"

#: Prefix used for aliased imports from the ``cesium`` package, so that Cesium
#: classes never collide with resium component names (``Entity``, ``Viewer``...).
CESIUM_IMPORT_PREFIX = "Cesium_"

#: Environment variable read for a Cesium ion access token.
#: (The variable *name*, not a secret.)
ION_TOKEN_ENV_VAR = "CESIUM_ION_ACCESS_TOKEN"  # noqa: S105  # nosec B105
