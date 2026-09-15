"""A tiny Python -> JavaScript bridge to the Cesium API.

Resium props are frequently *Cesium objects* (``Cartesian3``, ``Color``,
``ImageryLayer``...) that cannot be sent as JSON. This module builds real
JavaScript expressions as Reflex ``Var`` objects, so they can be passed to any
resium component prop and may reference state vars or ``rx.foreach`` items.

Example::

    from reflex_resium import Cesium, cartesian3, color

    Cesium.Cartesian3.fromDegrees(139.767, 35.681, 100)   # generic access
    Cesium.Color.RED.withAlpha(0.5)
    Cesium.HeightReference.CLAMP_TO_GROUND                # enums
    Cesium.OpenStreetMapImageryProvider.new(url="https://tile.openstreetmap.org/")
    cartesian3(State.lon, State.lat, 1000)                # helpers accept Vars

Every top-level Cesium name is imported from the ``cesium`` package with an
alias (``Cesium_Color``...) so it never collides with resium components.
"""

from __future__ import annotations

import dataclasses
import hashlib
from collections.abc import Sequence
from typing import Any

from reflex.utils.imports import ImportVar
from reflex.vars.base import LiteralVar, Var, VarData

from .constants import CESIUM_IMPORT_PREFIX

__all__ = [
    "Cesium",
    "CesiumExpr",
    "bounding_sphere",
    "camera_orientation",
    "cartesian2",
    "cartesian3",
    "cartesian3_array",
    "cartesian3_array_heights",
    "cesium_import",
    "color",
    "distance_display_condition",
    "ellipsoid_terrain",
    "heading_pitch_range",
    "heading_pitch_roll",
    "ion_imagery_layer",
    "ion_resource",
    "js",
    "julian_date",
    "natural_earth_imagery_layer",
    "near_far_scalar",
    "osm_imagery_layer",
    "rectangle_from_degrees",
    "time_interval_collection",
    "to_js",
    "url_template_imagery_layer",
    "world_terrain",
]


def _snake_to_camel(name: str) -> str:
    head, *tail = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in tail)


def to_js(value: Any) -> Var:
    """Convert a Python value (or Var) into a Var usable inside a JS expression.

    Args:
        value: Any JSON-serialisable Python value, or a Var.

    Returns:
        The equivalent Var.
    """
    if isinstance(value, Var):
        return value
    return LiteralVar.create(value)


def _collect_deps(values: Sequence[Any]) -> tuple[Var, ...]:
    """Collect non-literal (state/computed) vars referenced by arguments."""
    deps: list[Var] = []

    def visit(v: Any) -> None:
        if isinstance(v, CesiumExpr):
            deps.extend(v._resium_deps)
        elif isinstance(v, Var):
            if not isinstance(v, LiteralVar):
                deps.append(v)
        elif isinstance(v, dict):
            for item in v.values():
                visit(item)
        elif isinstance(v, (list, tuple)):
            for item in v:
                visit(item)

    for value in values:
        visit(value)
    seen: dict[str, Var] = {}
    for dep in deps:
        seen.setdefault(str(dep), dep)
    return tuple(seen.values())


@dataclasses.dataclass(eq=False, frozen=True, slots=True)
class CesiumExpr(Var):
    """A Var holding a JavaScript expression rooted in the Cesium namespace.

    Attribute access and calls build larger expressions::

        Cesium.Color.fromCssColorString("#ff0000").withAlpha(0.4)

    Names that clash with ``Var`` methods (``equals``, ``to``, ``range``,
    ``create``...) can be reached with :meth:`attr` / :meth:`call`.
    """

    _resium_deps: tuple = dataclasses.field(default=())

    _resium_volatile: bool = dataclasses.field(default=False)

    def __post_init__(self) -> None:
        # Var.__post_init__ may re-run __init__ to decode f-string Var markup,
        # which would reset the extra fields to their defaults.
        deps, volatile = self._resium_deps, self._resium_volatile
        Var.__post_init__(self)
        object.__setattr__(self, "_resium_deps", deps)
        object.__setattr__(self, "_resium_volatile", volatile)

    def __getattr__(self, name: str) -> CesiumExpr:
        if name.startswith("_"):
            raise AttributeError(name)
        return self.attr(name)

    def attr(self, name: str) -> CesiumExpr:
        """Access a property of this expression.

        Args:
            name: The JavaScript property name.

        Returns:
            The expression ``<self>.<name>``.
        """
        return CesiumExpr(
            _js_expr=f"{self._js_expr}.{name}",
            _var_type=Any,
            _var_data=self._var_data,
            _resium_deps=self._resium_deps,
            _resium_volatile=self._resium_volatile,
        )

    def _call(self, prefix: str, args: tuple, kwargs: dict) -> CesiumExpr:
        call_args = list(args)
        if kwargs:
            call_args.append({_snake_to_camel(k): v for k, v in kwargs.items()})
        js_args = [to_js(a) for a in call_args]
        return CesiumExpr(
            _js_expr=f"({prefix}{self._js_expr}({', '.join(str(a) for a in js_args)}))",
            _var_type=Any,
            _var_data=VarData.merge(self._var_data, *(a._get_all_var_data() for a in js_args)),
            _resium_deps=_collect_deps([self, *call_args]),
            _resium_volatile=self._resium_volatile
            or any(isinstance(a, CesiumExpr) and a._resium_volatile for a in call_args),
        )

    def __call__(self, *args: Any, **kwargs: Any) -> CesiumExpr:
        """Call this expression as a function.

        Keyword arguments are gathered into a trailing options object with
        camelCase keys (the usual Cesium ``options`` argument).

        Returns:
            The call expression.
        """
        return self._call("", args, kwargs)

    def call(self, name: str, *args: Any, **kwargs: Any) -> CesiumExpr:
        """Call a method by name (useful when it clashes with a Var method).

        Args:
            name: The method name.
            *args: Positional arguments.
            **kwargs: Options (camelCased into a trailing object).

        Returns:
            The call expression.
        """
        return self.attr(name)(*args, **kwargs)

    def new(self, *args: Any, **kwargs: Any) -> CesiumExpr:
        """Instantiate this expression as a constructor (``new X(...)``).

        Returns:
            The ``new`` expression.
        """
        return self._call("new ", args, kwargs)

    def _with_deps(self, *values: Any) -> CesiumExpr:
        return dataclasses.replace(self, _resium_deps=_collect_deps([self, *values]), _resium_volatile=False)

    def volatile(self) -> CesiumExpr:
        """Opt out of automatic memoization (re-evaluate on every render).

        Returns:
            A copy flagged as volatile.
        """
        return dataclasses.replace(self, _resium_volatile=True)

    def memo(self, *deps: Any) -> CesiumExpr:
        """Memoize the expression with React ``useMemo``.

        Cesium objects are recreated on every render unless memoized, which
        re-initialises resium elements whose *read-only* props change. Deps
        default to the state vars referenced by the expression.

        Args:
            *deps: Explicit dependencies (vars or values).

        Returns:
            A Var referencing the memoized value.
        """
        dep_vars = [to_js(d) for d in deps] if deps else list(self._resium_deps)
        dep_list = ", ".join(str(d) for d in dep_vars)
        # Only a stable identifier for the hook variable, not a security hash.
        digest = hashlib.md5(f"{self._js_expr}|{dep_list}".encode(), usedforsecurity=False).hexdigest()[:10]
        name = f"resium_memo_{digest}"
        hook = f"const {name} = useMemo(() => {self._js_expr}, [{dep_list}]);"
        inner = VarData.merge(
            self._var_data,
            *(d._get_all_var_data() for d in dep_vars),
            VarData(imports={"react": [ImportVar(tag="useMemo")]}),
        )
        return CesiumExpr(
            _js_expr=name,
            _var_type=Any,
            _var_data=VarData(
                imports={"react": [ImportVar(tag="useMemo")]},
                hooks={hook: inner},
            ),
            _resium_deps=(),
        )


def cesium_import(name: str) -> ImportVar:
    """The canonical aliased import of a Cesium export (``Name as Cesium_Name``).

    ``install=False``: the package itself is installed through the components'
    ``lib_dependencies`` (pinned version). All reflex-resium code must use this
    helper so identical imports merge instead of colliding.

    Args:
        name: The Cesium export name.

    Returns:
        The import var.
    """
    return ImportVar(tag=name, alias=f"{CESIUM_IMPORT_PREFIX}{name}", install=False)


class _CesiumNamespace:
    """``Cesium.<Name>`` returns an aliased import of ``<Name>`` from cesium."""

    def __getattr__(self, name: str) -> CesiumExpr:
        if name.startswith("_"):
            raise AttributeError(name)
        return self[name]

    def __getitem__(self, name: str) -> CesiumExpr:
        return CesiumExpr(
            _js_expr=f"{CESIUM_IMPORT_PREFIX}{name}",
            _var_type=Any,
            _var_data=VarData(imports={"cesium": [cesium_import(name)]}),
        )

    def __repr__(self) -> str:
        return "<Cesium namespace>"


#: Entry point to the whole Cesium API: ``Cesium.Cartesian3.fromDegrees(...)``.
Cesium = _CesiumNamespace()


def js(expression: str, *cesium_names: str, deps: Sequence[Any] | None = None) -> CesiumExpr:
    """Build a raw JavaScript expression.

    Vars may be interpolated with f-strings (``js(f"{State.value} * 2")``).

    Args:
        expression: JavaScript source. Use ``Cesium_<Name>`` to reference
            Cesium exports listed in ``cesium_names``.
        *cesium_names: Cesium exports to import for the expression.
        deps: Vars the expression depends on. When omitted the expression is
            *volatile* (never auto-memoized), because interpolated Vars cannot
            be detected reliably.

    Returns:
        The expression as a Var.
    """
    expr = CesiumExpr(
        _js_expr=f"({expression})",
        _var_type=Any,
        _var_data=VarData.merge(*(Cesium[n]._var_data for n in cesium_names)),
        _resium_volatile=deps is None,
    )
    if deps is not None:
        expr = expr._with_deps(*deps)
    return expr


# ---------------------------------------------------------------------------
# Helpers for the most common Cesium values
# ---------------------------------------------------------------------------


def cartesian3(longitude: Any, latitude: Any, height: Any = 0) -> CesiumExpr:
    """``Cartesian3.fromDegrees(longitude, latitude, height)``."""
    return Cesium.Cartesian3.fromDegrees(longitude, latitude, height)


def cartesian3_array(coordinates: Any) -> CesiumExpr:
    """``Cartesian3.fromDegreesArray([lon, lat, lon, lat, ...])``.

    Accepts a flat list or a list of ``[lon, lat]`` pairs (a Var is flattened in JS).
    """
    if isinstance(coordinates, (list, tuple)) and coordinates and isinstance(coordinates[0], (list, tuple)):
        coordinates = [c for pair in coordinates for c in pair[:2]]
    elif isinstance(coordinates, Var):
        coordinates = js(f"{coordinates}.flat()", deps=[coordinates])  # type: ignore[assignment]
    return Cesium.Cartesian3.fromDegreesArray(coordinates)


def cartesian3_array_heights(coordinates: Any) -> CesiumExpr:
    """``Cartesian3.fromDegreesArrayHeights([lon, lat, h, ...])``.

    Accepts a flat list or a list of ``[lon, lat, height]`` triples.
    """
    if isinstance(coordinates, (list, tuple)) and coordinates and isinstance(coordinates[0], (list, tuple)):
        coordinates = [c for triple in coordinates for c in triple[:3]]
    elif isinstance(coordinates, Var):
        coordinates = js(f"{coordinates}.flat()", deps=[coordinates])  # type: ignore[assignment]
    return Cesium.Cartesian3.fromDegreesArrayHeights(coordinates)


def cartesian2(x: Any, y: Any) -> CesiumExpr:
    """``new Cartesian2(x, y)`` (pixel offsets, scales...)."""
    return Cesium.Cartesian2.new(x, y)


def color(value: Any, alpha: Any = None) -> CesiumExpr:
    """A Cesium ``Color`` from a CSS color string (``"#ff0000"``, ``"red"``, ``"rgba(...)"``).

    Args:
        value: CSS color string or Var.
        alpha: Optional alpha override in ``[0, 1]``.

    Returns:
        The Color expression.
    """
    expr = Cesium.Color.fromCssColorString(value)
    if alpha is not None:
        expr = expr.withAlpha(alpha)
    return expr


def rectangle_from_degrees(west: Any, south: Any, east: Any, north: Any) -> CesiumExpr:
    """``Rectangle.fromDegrees(west, south, east, north)``."""
    return Cesium.Rectangle.fromDegrees(west, south, east, north)


def heading_pitch_roll(heading: Any = 0, pitch: Any = 0, roll: Any = 0) -> CesiumExpr:
    """``HeadingPitchRoll.fromDegrees(heading, pitch, roll)`` (degrees)."""
    return Cesium.HeadingPitchRoll.fromDegrees(heading, pitch, roll)


def heading_pitch_range(heading: Any = 0, pitch: Any = -45, range: Any = 1000) -> CesiumExpr:  # noqa: A002
    """``new HeadingPitchRange(...)`` from degrees and metres."""
    return Cesium.HeadingPitchRange.new(Cesium.Math.toRadians(heading), Cesium.Math.toRadians(pitch), range)


def camera_orientation(heading: Any = 0, pitch: Any = -90, roll: Any = 0) -> CesiumExpr:
    """Orientation object ``{heading, pitch, roll}`` in radians, from degrees.

    Suitable for ``CameraFlyTo(orientation=...)`` and ``Camera.setView``.
    """
    return js(
        f"{{heading: Cesium_Math.toRadians({to_js(heading)}), "
        f"pitch: Cesium_Math.toRadians({to_js(pitch)}), "
        f"roll: Cesium_Math.toRadians({to_js(roll)})}}",
        "Math",
        deps=[heading, pitch, roll],
    )


def near_far_scalar(near: Any, near_value: Any, far: Any, far_value: Any) -> CesiumExpr:
    """``new NearFarScalar(near, nearValue, far, farValue)``."""
    return Cesium.NearFarScalar.new(near, near_value, far, far_value)


def distance_display_condition(near: Any = 0, far: Any = 1e20) -> CesiumExpr:
    """``new DistanceDisplayCondition(near, far)``."""
    return Cesium.DistanceDisplayCondition.new(near, far)


def bounding_sphere(longitude: Any, latitude: Any, height: Any, radius: Any) -> CesiumExpr:
    """``new BoundingSphere(Cartesian3.fromDegrees(...), radius)``."""
    return Cesium.BoundingSphere.new(cartesian3(longitude, latitude, height), radius)


def julian_date(iso8601: Any) -> CesiumExpr:
    """``JulianDate.fromIso8601(iso)``."""
    return Cesium.JulianDate.fromIso8601(iso8601)


def time_interval_collection(iso8601_interval: Any) -> CesiumExpr:
    """``TimeIntervalCollection.fromIso8601({iso8601: "start/stop"})``."""
    return Cesium.TimeIntervalCollection.fromIso8601(iso8601=iso8601_interval)


def ion_resource(asset_id: Any, **options: Any) -> CesiumExpr:
    """``IonResource.fromAssetId(assetId, options)`` (needs an ion token)."""
    if options:
        return Cesium.IonResource.fromAssetId(asset_id, **options)
    return Cesium.IonResource.fromAssetId(asset_id)


def osm_imagery_layer(url: str = "https://tile.openstreetmap.org/") -> CesiumExpr:
    """An ``ImageryLayer`` backed by OpenStreetMap tiles (memoized, no token)."""
    return Cesium.ImageryLayer.new(Cesium.OpenStreetMapImageryProvider.new(url=url)).memo()


def natural_earth_imagery_layer() -> CesiumExpr:
    """Natural Earth II imagery bundled inside Cesium's own assets.

    Works offline (served from ``CESIUM_BASE_URL``) and needs no token.
    """
    return Cesium.ImageryLayer.fromProviderAsync(
        Cesium.TileMapServiceImageryProvider.fromUrl(Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII"))
    ).memo()


def url_template_imagery_layer(url: str, **options: Any) -> CesiumExpr:
    """An ``ImageryLayer`` backed by a ``{z}/{x}/{y}`` URL template (memoized)."""
    return Cesium.ImageryLayer.new(Cesium.UrlTemplateImageryProvider.new(url=url, **options)).memo()


def ion_imagery_layer(asset_id: int = 2) -> CesiumExpr:
    """An ``ImageryLayer`` from a Cesium ion imagery asset (memoized, needs token)."""
    return Cesium.ImageryLayer.fromProviderAsync(Cesium.IonImageryProvider.fromAssetId(asset_id)).memo()


def world_terrain(**options: Any) -> CesiumExpr:
    """``createWorldTerrainAsync(options)`` for Viewer ``terrain_provider`` (memoized)."""
    return Cesium.createWorldTerrainAsync(**options).memo() if options else Cesium.createWorldTerrainAsync().memo()


def ellipsoid_terrain() -> CesiumExpr:
    """``new EllipsoidTerrainProvider()`` (flat globe, memoized)."""
    return Cesium.EllipsoidTerrainProvider.new().memo()
