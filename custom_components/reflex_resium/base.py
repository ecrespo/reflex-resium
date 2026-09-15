"""Base class shared by every resium component wrapper."""

from __future__ import annotations

import json
from typing import Any, ClassVar

import reflex as rx
from reflex.utils.imports import ImportVar
from reflex.vars.base import LiteralVar, Var

from .cesium import CesiumExpr, cesium_import
from .constants import CESIUM_LIBRARY, CESIUM_WIDGETS_CSS, RESIUM_LIBRARY
from .plugin import get_cesium_base_url, get_ion_access_token

__all__ = ["ResiumCameraOperation", "ResiumComponent", "resium_setup_code"]


def resium_setup_code() -> str:
    """JavaScript executed once per page before any Cesium element is created.

    Returns:
        The setup snippet (``CESIUM_BASE_URL`` and optional ion token).
    """
    code = (
        'if (typeof window !== "undefined" && window.CESIUM_BASE_URL === undefined) '
        f"{{ window.CESIUM_BASE_URL = {json.dumps(get_cesium_base_url())}; }}"
    )
    token = get_ion_access_token()
    if token:
        code += f'\nif (typeof window !== "undefined") {{ Cesium_Ion.defaultAccessToken = {json.dumps(token)}; }}'
    return code


def _is_memoizable(expr: CesiumExpr) -> bool:
    """Only memoize when every dependency is a state var (not a foreach item)."""
    if expr._resium_volatile or expr._js_expr.startswith("resium_memo_"):
        return False
    for dep in expr._resium_deps:
        data = dep._get_all_var_data()
        if data is None or not data.state:
            return False
    return True


class ResiumComponent(rx.Component):
    """Base for all resium wrappers: npm packages, CSS and Cesium setup."""

    library = RESIUM_LIBRARY

    lib_dependencies: list[str] = [CESIUM_LIBRARY]

    # Python names of "Cesium read-only props" (changing them re-creates the element).
    _resium_readonly_props: ClassVar[tuple[str, ...]] = ()

    # Python prop name -> JS prop name, for props that clash with Reflex fields.
    _resium_renamed_props: ClassVar[dict[str, str]] = {}

    @classmethod
    def create(cls, *children: Any, **props: Any) -> rx.Component:
        """Create the component, memoizing Cesium objects passed as props.

        Every :class:`~reflex_resium.cesium.CesiumExpr` prop whose dependencies
        are state vars (or constants) is wrapped in ``useMemo``, so Cesium
        objects keep their identity between renders. This matters most for
        "read-only" props, whose change re-creates the Cesium element, and for
        camera operations such as ``CameraFlyTo`` that restart when props change.

        Args:
            *children: Child components.
            **props: Component props.

        Returns:
            The component.
        """
        for name, value in list(props.items()):
            if isinstance(value, CesiumExpr) and _is_memoizable(value):
                props[name] = value.memo()
        custom_attrs = dict(props.pop("custom_attrs", None) or {})
        for py_name, js_name in cls._resium_renamed_props.items():
            if py_name in props:
                value = props.pop(py_name)
                custom_attrs[js_name] = value if isinstance(value, Var) else LiteralVar.create(value)
        if custom_attrs:
            props["custom_attrs"] = custom_attrs
        return super().create(*children, **props)

    def add_imports(self) -> dict[str, Any]:
        """Import Cesium's widget stylesheet (and ``Ion`` when a token is set).

        Returns:
            The imports.
        """
        imports: dict[str, Any] = {"": CESIUM_WIDGETS_CSS}
        if get_ion_access_token():
            imports["cesium"] = [cesium_import("Ion")]
        return imports

    def add_custom_code(self) -> list[str]:
        """Emit the page-level Cesium setup snippet.

        Returns:
            The custom code.
        """
        return [resium_setup_code()]


_STABLE_PROPS_EQUAL_JS = """
function __resiumStablePropsEqual(prev, next) {
  const keys = new Set([...Object.keys(prev), ...Object.keys(next)]);
  for (const key of keys) {
    if (key === "children") continue;
    const a = prev[key];
    const b = next[key];
    if (typeof a === "function" && typeof b === "function") continue;
    if (a !== b) return false;
  }
  return true;
}
"""


class ResiumCameraOperation(ResiumComponent):
    """Base for camera operations (``CameraFlyTo``, ``CameraLookAt``...).

    resium runs camera operations in an effect *on every render*. Reflex
    re-renders a page subtree whenever any state var it uses changes (a mouse
    move, a slider...), which would restart the flight each time. These
    wrappers render the resium component through ``React.memo`` with a
    comparison that ignores callback identity, so the operation only runs
    again when a real prop (destination, duration, orientation...) changes.
    """

    library = None  # type: ignore[assignment]

    lib_dependencies: list[str] = [CESIUM_LIBRARY, RESIUM_LIBRARY]

    # Name of the resium export wrapped by this component.
    _resium_source_tag: ClassVar[str] = ""

    def add_imports(self) -> dict[str, Any]:
        """Import the original resium component and ``React.memo``.

        Returns:
            The imports.
        """
        return {
            **super().add_imports(),
            "react": [ImportVar(tag="memo")],
            "resium": [
                ImportVar(
                    tag=self._resium_source_tag,
                    alias=f"Resium_{self._resium_source_tag}",
                    install=False,
                )
            ],
        }

    def add_custom_code(self) -> list[str]:
        """Define the memoized wrapper.

        Returns:
            The custom code.
        """
        return [
            *super().add_custom_code(),
            _STABLE_PROPS_EQUAL_JS,
            f"const {self.tag} = memo(Resium_{self._resium_source_tag}, __resiumStablePropsEqual);",
        ]
