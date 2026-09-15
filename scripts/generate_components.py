"""Generate ``custom_components/reflex_resium/components.py`` from resium.

Pipeline (run from the repository root):

1. ``node scripts/extract_props.mjs`` (inside a folder where ``resium``,
   ``cesium``, ``react`` and ``typescript@5`` are installed) resolves every
   component's props with the TypeScript compiler into ``props.json``.
2. ``python scripts/generate_components.py props.json path/to/resium/src``
   writes the Python wrappers (prop types, docs, read-only props, events).

The resium source tree is used for component summaries and the list of
"Cesium read-only props" (props that re-create the Cesium element).
"""

from __future__ import annotations

import json
import keyword
import re
import sys
import textwrap
from pathlib import Path

ROOT_COMPONENTS = {"Viewer", "CesiumWidget"}
# resium camera operations run on every render; they get a memoized wrapper.
CAMERA_OPERATIONS = {"CameraFlyTo", "CameraFlyHome", "CameraFlyToBoundingSphere", "CameraLookAt"}
SKIP_COMPONENTS = {"CesiumContext", "Provider", "Consumer"}
# Props already provided by rx.Component with identical semantics.
INHERITED_PROPS = {"id", "className", "children", "key", "ref"}
# Root components keep Reflex's `style`; elsewhere `style` is a Cesium value.
ROOT_STYLE = "style"
# camelCase names whose snake_case form does not round-trip through Reflex.
FORCED_RENAMES = {
    "tileMatrixSetID": "tile_matrix_set_id",
    "useWebVR": "use_web_vr",
    "scene3DOnly": "scene_3d_only",
    "mapMode2D": "map_mode_2d",
}

# Files that define several components.
MULTI_COMPONENT_FILES = {
    "BlackAndWhiteStage": "PostProcessStage",
    "BrightnessStage": "PostProcessStage",
    "LensFlareStage": "PostProcessStage",
    "Fxaa": "PostProcessStage",
    "NightVisionStage": "PostProcessStage",
    "AmbientOcclusion": "PostProcessStageComposite",
    "Bloom": "PostProcessStageComposite",
    "BlurStage": "PostProcessStageComposite",
    "DepthOfFieldStage": "PostProcessStageComposite",
    "EdgeDetectionStage": "PostProcessStageComposite",
    "SilhouetteStage": "PostProcessStageComposite",
}


def snake(name: str) -> str:
    name = name.replace("3D", "3d").replace("2D", "2d")
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", name).lower()
    return re.sub(r"([a-z])([23]d)(?=_|$)", r"\1_\2", name)


def camel_to_snake(name: str) -> str:
    if name in FORCED_RENAMES:
        return FORCED_RENAMES[name]
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name).lower()


def read_source(src: Path, component: str) -> str:
    folder = MULTI_COMPONENT_FILES.get(component, component)
    for ext in (".ts", ".tsx"):
        path = src / folder / f"{folder}{ext}"
        if path.exists():
            return path.read_text()
    return ""


def block(source: str, tag: str) -> str:
    match = re.search(rf"/\*\s*\n@{tag}\n(.*?)\*/", source, re.S)
    return match.group(1).strip() if match else ""


def string_list(source: str, const: str) -> list[str]:
    match = re.search(rf"const {const} = \[(.*?)\] as const", source, re.S)
    return re.findall(r'"([^"]+)"', match.group(1)) if match else []


def py_type(kinds: list[str]) -> str:
    clean = [k for k in kinds if k != "null"]
    if clean == ["boolean"]:
        return "bool"
    if clean == ["number"]:
        return "float"
    if clean == ["string"]:
        return "str"
    return "Any"


def event_spec(prop: dict) -> str:
    name = prop["name"]
    params = prop.get("params") or []
    types = [p["type"] for p in params]
    if not params:
        return "no_args_event"
    if types and types[0] == "CesiumMovementEvent":
        return "movement_event"
    if name == "onWheel":
        return "wheel_event"
    if types == ["number"]:
        return "number_event"
    if types == ["number", "number"]:
        return "two_numbers_event"
    if types == ["Entity | undefined"]:
        return "entity_event"
    if types == ["Clock"]:
        return "clock_event"
    if types == ["ImageryLayer", "number"]:
        return "imagery_layer_event"
    if types == ["Particle", "number"]:
        return "particle_event"
    if types[0].endswith("DataSource"):
        if len(types) == 1:
            return "data_source_event"
        if types[1] == "boolean":
            return "data_source_loading_event"
        if types[1] == "string":
            return "kml_refresh_event"
        return "data_source_error_event"
    if name in {"onError", "onTileFailed", "onRenderError"} or types[0] in {"any", "unknown"}:
        return "error_event"
    return "object_event"


def comment(text: str, indent: str = "    ") -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    return [f"{indent}# {line}" for line in textwrap.wrap(text, 92)]


def docstring(component: str, source: str) -> str:
    summary = block(source, "summary")
    scope = block(source, "scope")
    # Keep the first paragraph of the summary; drop markdown links/code fences.
    first = summary.split("\n\n")[0] if summary else f"Resium `{component}` component."
    first = re.sub(r"\[`?([^`\]]+)`?\]\([^)]+\)", r"\1", first).replace("`", "")
    scope_text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", scope).replace("`", "")
    lines = [f"Wraps resium ``{component}``.", "", *textwrap.wrap(first, 84)]
    if scope_text:
        lines += ["", "Scope:", *("  " + ln for ln in scope_text.splitlines() if ln.strip())]
    lines += ["", f"Docs: https://resium.reearth.io/components/{component}"]
    body = "\n".join(("    " + ln) if ln else "" for ln in lines).lstrip().replace('"""', "'''").replace("\\", "\\\\")
    return f'    """{body}\n    """'


def generate(props_json: Path, src: Path) -> str:
    data = json.loads(props_json.read_text())
    out: list[str] = [
        '"""Resium component wrappers for Reflex.',
        "",
        "AUTO-GENERATED by scripts/generate_components.py from resium's TypeScript",
        "definitions. Do not edit by hand; regenerate instead.",
        '"""',
        "",
        "# ruff: noqa: E501",
        "from __future__ import annotations",
        "",
        "from typing import Any",
        "",
        "import reflex as rx",
        "",
        "from .base import ResiumCameraOperation, ResiumComponent",
        "from .events import (",
        *(
            f"    {n},"
            for n in sorted(
                {
                    "clock_event",
                    "data_source_error_event",
                    "data_source_event",
                    "data_source_loading_event",
                    "entity_event",
                    "error_event",
                    "imagery_layer_event",
                    "kml_refresh_event",
                    "movement_event",
                    "no_args_event",
                    "number_event",
                    "object_event",
                    "particle_event",
                    "screen_space_action_event",
                    "two_numbers_event",
                    "wheel_event",
                }
            )
        ),
        ")",
        "",
    ]
    exports: list[str] = []
    for component, props in data.items():
        if component in SKIP_COMPONENTS:
            continue
        source = read_source(src, component)
        readonly = set(string_list(source, "cesiumReadonlyProps"))
        is_root = component in ROOT_COMPONENTS
        if component in CAMERA_OPERATIONS:
            out += ["", f"class {component}(ResiumCameraOperation):", docstring(component, source), ""]
            out.append(f'    tag = "ResiumStable{component}"')
            out.append("")
            out.append(f'    _resium_source_tag = "{component}"')
        else:
            out += ["", f"class {component}(ResiumComponent):", docstring(component, source), ""]
            out.append(f'    tag = "{component}"')
        out.append("")
        readonly_py: list[str] = []
        renamed: dict[str, str] = {}
        events: list[str] = []
        for prop in props:
            name = prop["name"]
            if name in INHERITED_PROPS or (is_root and name == ROOT_STYLE):
                continue
            is_function = "function" in prop["kinds"]
            if (is_function and re.match(r"^on[A-Z]", name)) or name == "action":
                spec = "screen_space_action_event" if name == "action" else event_spec(prop)
                py_name = camel_to_snake(name)
                sig = ", ".join(f"{p['name']}: {p['type']}" for p in prop.get("params") or [])
                events += [
                    *comment(f"{name}({sig})" + (f" — {prop['doc']}" if prop["doc"] else "")),
                    f"    {py_name}: rx.EventHandler[{spec}]",
                    "",
                ]
                continue
            py_name = camel_to_snake(name)
            if name == "style":
                py_name = "cesium_style"
                renamed[py_name] = "style"
            elif name in FORCED_RENAMES:
                renamed[py_name] = name
            if keyword.iskeyword(py_name):
                py_name += "_"
            annotation = "Any" if is_function else py_type(prop["kinds"])
            notes = [prop["doc"]] if prop["doc"] else []
            notes.append(f"Type: {prop['type'].replace(' | undefined', '')}.")
            if name in readonly:
                notes.append("Read-only: changing it re-creates the Cesium element.")
                readonly_py.append(py_name)
            if not prop.get("optional", True):
                notes.append("Required.")
            out += comment(" ".join(notes))
            out.append(f"    {py_name}: rx.Var[{annotation}]")
            out.append("")
        out += events
        if readonly_py:
            out.append(f"    _resium_readonly_props = {tuple(readonly_py)!r}")
            out.append("")
        if renamed:
            out.append(f"    _resium_renamed_props = {renamed!r}")
            out.append("")
        if component == "CesiumWidget":
            out += [
                "    @classmethod",
                "    def create(cls, *children: Any, **props: Any) -> rx.Component:",
                '        """Create the widget; children get the entity/data source context.',
                "",
                "        resium's CesiumWidget does not provide Cesium's ``entities`` and",
                "        ``dataSources`` collections, so children are wrapped with",
                "        :class:`~reflex_resium.bridge.CesiumWidgetContext`.",
                '        """',
                "        from .bridge import CesiumWidgetContext",
                "",
                "        return super().create(CesiumWidgetContext.create(*children), **props)",
                "",
            ]
        factory = snake(component)
        out += ["", f"{factory} = {component}.create", ""]
        exports += [component, factory]
    out += ["", "__all__ = ["] + [f'    "{e}",' for e in exports] + ["]", ""]
    return "\n".join(out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: generate_components.py props.json path/to/resium/src")
    target = Path(__file__).resolve().parents[1] / "custom_components" / "reflex_resium" / "components.py"
    target.write_text(generate(Path(sys.argv[1]), Path(sys.argv[2])))
    print(f"wrote {target}")
