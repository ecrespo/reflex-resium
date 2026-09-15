"""Event specs that turn resium/Cesium callback arguments into JSON.

Cesium hands its callbacks live objects (``Entity``, ``Cesium3DTileset``,
``Clock``...) that are circular and cannot cross the websocket. Each spec below
converts them, in the browser, into small JSON-safe dictionaries before the
event is sent to the Reflex backend.
"""

from __future__ import annotations

from typing import Any

from reflex.vars.base import Var

__all__ = [
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
]

_PRIMITIVE = '(v) => v === null || ["string", "number", "boolean"].includes(typeof v)'

#: JS function: Cartesian2 -> {x, y}.
JS_CARTESIAN2 = "((p) => (p ? { x: p.x, y: p.y } : null))"

#: JS function: CesiumMovementEvent -> {position, start_position, end_position}.
JS_MOVEMENT = (
    "((m) => (m ? { "
    f"position: {JS_CARTESIAN2}(m.position), "
    f"start_position: {JS_CARTESIAN2}(m.startPosition), "
    f"end_position: {JS_CARTESIAN2}(m.endPosition) "
    "} : null))"
)

#: JS function: picked object / Entity / Cesium3DTileFeature -> summary dict.
JS_PICKED = (
    "((t) => { try { if (t == null) return null; "
    f"const isPrim = {_PRIMITIVE}; "
    'const ent = t.id && typeof t.id === "object" ? t.id : (t.propertyNames !== undefined && t.entityCollection !== undefined ? t : null); '
    'const feature = typeof t.getPropertyIds === "function" ? t : null; '
    "const properties = {}; "
    "if (feature) { for (const k of feature.getPropertyIds()) { const v = feature.getProperty(k); if (isPrim(v)) properties[k] = v; } } "
    'else if (ent && ent.properties && typeof ent.properties.getValue === "function") { const bag = ent.properties.getValue() || {}; for (const k in bag) { if (isPrim(bag[k])) properties[k] = bag[k]; } } '
    "return { "
    "id: ent ? ent.id : (isPrim(t.id) ? t.id : null), "
    "name: ent ? (ent.name ?? null) : (isPrim(t.name) ? t.name ?? null : null), "
    'kind: ent ? "entity" : feature ? "feature" : "primitive", '
    "properties }; } catch (e) { return null; } })"
)

#: JS function: Entity | undefined -> {id, name} | null.
JS_ENTITY = "((e) => (e ? { id: e.id ?? null, name: e.name ?? null } : null))"

#: JS function: Clock -> summary dict.
JS_CLOCK = (
    "((c) => (c ? { "
    "current_time: c.currentTime ? c.currentTime.toString() : null, "
    "start_time: c.startTime ? c.startTime.toString() : null, "
    "stop_time: c.stopTime ? c.stopTime.toString() : null, "
    "multiplier: c.multiplier, should_animate: c.shouldAnimate "
    "} : null))"
)

#: JS function: DataSource -> summary dict.
JS_DATA_SOURCE = (
    "((d) => { try { return d ? { name: d.name ?? null, "
    "entity_count: d.entities ? d.entities.values.length : 0, "
    "is_loading: !!d.isLoading, show: d.show } : null; } catch (e) { return null; } })"
)

#: JS function: ImageryLayer -> summary dict.
JS_IMAGERY_LAYER = "((l) => (l ? { show: l.show, alpha: l.alpha } : null))"

#: JS function: error-like -> string.
JS_ERROR = "((e) => (e == null ? null : String(e && e.message ? e.message : e)))"

#: JS function: any Cesium object -> small JSON-safe summary.
JS_OBJECT = (
    "((o) => { try { if (o == null) return null; "
    f"const isPrim = {_PRIMITIVE}; "
    "if (isPrim(o)) return o; "
    "const out = {}; "
    'for (const k of ["id", "name", "show", "url", "basePath", "ready"]) { try { if (isPrim(o[k])) out[k] = o[k]; } catch (e) {} } '
    "try { const bs = o.boundingSphere; if (bs && bs.center) { const c = bs.center; "
    "const a = 6378137, e2 = 6.69437999014e-3, b = a * Math.sqrt(1 - e2), ep2 = (a * a - b * b) / (b * b); "
    "const p = Math.hypot(c.x, c.y), th = Math.atan2(c.z * a, p * b); "
    "const lat = Math.atan2(c.z + ep2 * b * Math.sin(th) ** 3, p - e2 * a * Math.cos(th) ** 3); "
    "out.bounding_sphere = { longitude: Math.atan2(c.y, c.x) * 180 / Math.PI, latitude: lat * 180 / Math.PI, "
    "radius: bs.radius }; } } catch (e) {} "
    "return out; } catch (e) { return null; } })"
)


def _js(expression: str, *args: Var) -> Var[Any]:
    return Var(_js_expr=f"{expression}({', '.join(str(a) for a in args)})")


def no_args_event() -> tuple[()]:
    """Callback without arguments (``onComplete``, ``onMoveEnd``...)."""
    return ()


def movement_event(movement: Var, target: Var) -> tuple[Var[dict[str, Any]], Var[dict[str, Any]]]:
    """Mouse/touch events: ``(movement, target)``.

    The handler receives ``movement`` (``{"position": {"x", "y"}, "start_position",
    "end_position"}``) and ``target`` (``{"id", "name", "kind", "properties"}`` or ``None``).
    """
    return (_js(JS_MOVEMENT, movement), _js(JS_PICKED, target))


def screen_space_action_event(e: Var) -> tuple[Var[dict[str, Any]]]:
    """``ScreenSpaceEvent.action``: receives the movement dictionary."""
    return (_js(JS_MOVEMENT, e),)


def wheel_event(delta: Var) -> tuple[Var[float]]:
    """``onWheel``: receives the wheel delta."""
    return (delta,)


def number_event(value: Var) -> tuple[Var[float]]:
    """Callback with a single number."""
    return (value,)


def two_numbers_event(a: Var, b: Var) -> tuple[Var[float], Var[float]]:
    """Callback with two numbers (e.g. ``onLoadProgress``)."""
    return (a, b)


def entity_event(entity: Var) -> tuple[Var[dict[str, Any] | None]]:
    """``onSelectedEntityChange`` / ``onTrackedEntityChange``: ``{"id", "name"}`` or ``None``."""
    return (_js(JS_ENTITY, entity),)


def clock_event(clock: Var) -> tuple[Var[dict[str, Any]]]:
    """``Clock.onTick`` / ``onStop``: ISO-8601 times, multiplier, should_animate."""
    return (_js(JS_CLOCK, clock),)


def data_source_event(data_source: Var) -> tuple[Var[dict[str, Any]]]:
    """Data source ``onLoad`` / ``onChange``: ``{"name", "entity_count", ...}``."""
    return (_js(JS_DATA_SOURCE, data_source),)


def data_source_error_event(data_source: Var, error: Var) -> tuple[Var[dict[str, Any]], Var[str]]:
    """Data source ``onError``: ``(data_source, error_message)``."""
    return (_js(JS_DATA_SOURCE, data_source), _js(JS_ERROR, error))


def data_source_loading_event(data_source: Var, is_loading: Var) -> tuple[Var[dict[str, Any]], Var[bool]]:
    """Data source ``onLoading``: ``(data_source, is_loading)``."""
    return (_js(JS_DATA_SOURCE, data_source), is_loading)


def kml_refresh_event(data_source: Var, url: Var) -> tuple[Var[dict[str, Any]], Var[str]]:
    """``KmlDataSource.onRefresh``: ``(data_source, url)``."""
    return (_js(JS_DATA_SOURCE, data_source), url)


def imagery_layer_event(layer: Var, index: Var) -> tuple[Var[dict[str, Any]], Var[float]]:
    """ImageryLayerCollection ``onLayerAdd`` / ``Remove`` / ``Move`` / ``ShowOrHide``."""
    return (_js(JS_IMAGERY_LAYER, layer), index)


def particle_event(particle: Var, dt: Var) -> tuple[Var[float]]:
    """``ParticleSystem.onUpdate``: only the time delta is sent (per-particle, high frequency)."""
    return (dt,)


def error_event(error: Var) -> tuple[Var[str]]:
    """``onError`` / ``onTileFailed``: the error message."""
    return (_js(JS_ERROR, error),)


def object_event(obj: Var) -> tuple[Var[dict[str, Any]]]:
    """Generic Cesium object callback (``onReady``, ``onTileLoad``...): a summary dict."""
    return (_js(JS_OBJECT, obj),)
