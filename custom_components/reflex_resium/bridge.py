"""Reflex-specific helpers that go beyond resium's own components.

* :class:`CesiumEvents` — mount inside ``viewer``/``cesium_widget`` to receive
  *geographic* events (longitude/latitude/height of clicks and mouse moves,
  camera changes, entity selection) as JSON in your Reflex state.
* ``fly_to``, ``set_view``, ``zoom_to_entity``... — imperative camera/clock
  actions returned as ``rx.call_script`` event specs, usable from any event
  handler or ``on_click``. They target the viewer registered by
  ``CesiumEvents(viewer_id=...)``.
"""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex.event import EventSpec
from reflex.utils.imports import ImportVar
from reflex.vars.base import Var, VarData

from .base import ResiumComponent
from .cesium import cesium_import, to_js
from .events import JS_PICKED

__all__ = [
    "CesiumEvents",
    "CesiumWidgetContext",
    "cesium_events",
    "fly_home",
    "fly_to",
    "get_camera",
    "morph_to",
    "screenshot",
    "set_clock",
    "set_view",
    "zoom_to_entity",
]

_BRIDGE_JS = r"""
const __resiumToDeg = (r) => Cesium_Math.toDegrees(r);
const __resiumPicked = %(picked)s;
function __resiumCameraInfo(camera) {
  if (!camera) return null;
  const c = camera.positionCartographic;
  return {
    longitude: __resiumToDeg(c.longitude), latitude: __resiumToDeg(c.latitude), height: c.height,
    heading: __resiumToDeg(camera.heading), pitch: __resiumToDeg(camera.pitch), roll: __resiumToDeg(camera.roll),
  };
}
function __resiumLocate(scene, camera, position, pickEntities) {
  if (!scene || !position) return null;
  let cartesian;
  let picked;
  try { picked = pickEntities ? scene.pick(position) : undefined; } catch (e) { picked = undefined; }
  if (picked && scene.pickPositionSupported) { try { cartesian = scene.pickPosition(position); } catch (e) {} }
  if (!cartesian && scene.globe) { const ray = camera.getPickRay(position); if (ray) cartesian = scene.globe.pick(ray, scene); }
  if (!cartesian) cartesian = camera.pickEllipsoid(position, scene.globe ? scene.globe.ellipsoid : undefined);
  const carto = cartesian ? Cesium_Cartographic.fromCartesian(cartesian) : undefined;
  return {
    screen: { x: position.x, y: position.y },
    longitude: carto ? __resiumToDeg(carto.longitude) : null,
    latitude: carto ? __resiumToDeg(carto.latitude) : null,
    height: carto ? carto.height : null,
    picked: __resiumPicked(picked),
  };
}
if (typeof window !== "undefined" && !window.reflexResiumApi) {
  const viewers = (window.reflexResium = window.reflexResium || {});
  const get = (id) => viewers[id];
  const destination = (o) => Cesium_Cartesian3.fromDegrees(o.longitude, o.latitude, o.height ?? 10000);
  const orientation = (o) => ({ heading: Cesium_Math.toRadians(o.heading ?? 0), pitch: Cesium_Math.toRadians(o.pitch ?? -90), roll: Cesium_Math.toRadians(o.roll ?? 0) });
  const findEntity = (v, entityId) => {
    let e = v.entities ? v.entities.getById(entityId) : undefined;
    if (!e && v.dataSources) { for (let i = 0; i < v.dataSources.length && !e; i++) e = v.dataSources.get(i).entities.getById(entityId); }
    return e;
  };
  window.reflexResiumApi = {
    flyTo(id, o) { const v = get(id); if (v) v.camera.flyTo({ destination: destination(o), orientation: orientation(o), duration: o.duration }); },
    setView(id, o) { const v = get(id); if (v) v.camera.setView({ destination: destination(o), orientation: orientation(o) }); },
    flyHome(id, duration) { const v = get(id); if (v) v.camera.flyHome(duration); },
    zoomTo(id, entityId, fly, duration) { const v = get(id); if (!v || !v.zoomTo) return; const e = findEntity(v, entityId); if (!e) return; return fly ? v.flyTo(e, { duration }) : v.zoomTo(e); },
    morph(id, mode, duration) { const v = get(id); if (!v) return; const s = v.scene; if (mode === "2D") s.morphTo2D(duration); else if (mode === "COLUMBUS_VIEW") s.morphToColumbusView(duration); else s.morphTo3D(duration); },
    setClock(id, o) { const v = get(id); if (!v || !v.clock) return; const c = v.clock; if (o.current_time) c.currentTime = Cesium_JulianDate.fromIso8601(o.current_time); if (o.multiplier !== undefined && o.multiplier !== null) c.multiplier = o.multiplier; if (o.should_animate !== undefined && o.should_animate !== null) c.shouldAnimate = o.should_animate; },
    camera(id) { const v = get(id); return v ? __resiumCameraInfo(v.camera) : null; },
    screenshot(id) { const v = get(id); if (!v) return null; v.render(); return v.canvas.toDataURL("image/png"); },
  };
}
function ReflexResiumEvents({ viewerId, mouseMoveThrottle = 100, pickEntities = true, onLeftClick, onDoubleClick, onRightClick, onMouseMove, onCameraChange, onSelectedEntityChange, onReady }) {
  const ctx = useCesium();
  const { scene, camera } = ctx;
  const owner = ctx.viewer || ctx.cesiumWidget;
  const handlers = useRef({});
  handlers.current = { onLeftClick, onDoubleClick, onRightClick, onMouseMove, onCameraChange, onSelectedEntityChange, onReady };
  useEffect(() => {
    if (!viewerId || !owner || typeof window === "undefined") return undefined;
    window.reflexResium = window.reflexResium || {};
    window.reflexResium[viewerId] = owner;
    return () => { if (window.reflexResium[viewerId] === owner) delete window.reflexResium[viewerId]; };
  }, [viewerId, owner]);
  useEffect(() => {
    if (!scene || !camera) return undefined;
    const sshe = new Cesium_ScreenSpaceEventHandler(scene.canvas);
    const T = Cesium_ScreenSpaceEventType;
    const bind = (name, type) => sshe.setInputAction((m) => { const cb = handlers.current[name]; if (cb) cb(__resiumLocate(scene, camera, m.position, pickEntities)); }, type);
    bind("onLeftClick", T.LEFT_CLICK);
    bind("onDoubleClick", T.LEFT_DOUBLE_CLICK);
    bind("onRightClick", T.RIGHT_CLICK);
    let last = 0;
    sshe.setInputAction((m) => {
      const cb = handlers.current.onMouseMove;
      if (!cb) return;
      const now = Date.now();
      if (now - last < mouseMoveThrottle) return;
      last = now;
      cb(__resiumLocate(scene, camera, m.endPosition, pickEntities));
    }, T.MOUSE_MOVE);
    const offCamera = camera.moveEnd.addEventListener(() => { const cb = handlers.current.onCameraChange; if (cb) cb(__resiumCameraInfo(camera)); });
    const offSelected = ctx.viewer ? ctx.viewer.selectedEntityChanged.addEventListener((e) => { const cb = handlers.current.onSelectedEntityChange; if (cb) cb(e ? { id: e.id ?? null, name: e.name ?? null } : null); }) : undefined;
    if (handlers.current.onReady) handlers.current.onReady(__resiumCameraInfo(camera));
    return () => { if (!sshe.isDestroyed()) sshe.destroy(); offCamera(); if (offSelected) offSelected(); };
  }, [scene, camera, ctx.viewer, pickEntities, mouseMoveThrottle]);
  return null;
}
""" % {"picked": JS_PICKED}


def _location_spec(info: Var) -> tuple[Var[dict[str, Any]]]:
    return (info,)


def _entity_spec(entity: Var) -> tuple[Var[dict[str, Any] | None]]:
    return (entity,)


class CesiumEvents(ResiumComponent):
    """Geographic events + viewer registration (a Reflex-only helper).

    Place it inside ``viewer(...)`` or ``cesium_widget(...)``. Every event
    receives plain dictionaries:

    * location events: ``{"longitude", "latitude", "height", "screen": {"x", "y"},
      "picked": {"id", "name", "kind", "properties"} | None}``
    * camera events: ``{"longitude", "latitude", "height", "heading", "pitch", "roll"}``
    """

    library = None  # type: ignore[assignment]

    tag = "ReflexResiumEvents"

    # Registers the Cesium viewer under this id for fly_to/set_view/... helpers.
    viewer_id: rx.Var[str]

    # Minimum milliseconds between two ``on_mouse_move`` events (default 100).
    mouse_move_throttle: rx.Var[int]

    # Pick entities/primitives under the cursor (default True).
    pick_entities: rx.Var[bool]

    # Left click on the globe or an object.
    on_left_click: rx.EventHandler[_location_spec]

    # Double click.
    on_double_click: rx.EventHandler[_location_spec]

    # Right click.
    on_right_click: rx.EventHandler[_location_spec]

    # Throttled mouse move.
    on_mouse_move: rx.EventHandler[_location_spec]

    # Fired when the camera stops moving.
    on_camera_change: rx.EventHandler[_location_spec]

    # Viewer selected entity changed (Viewer only): ``{"id", "name"}`` or None.
    on_selected_entity_change: rx.EventHandler[_entity_spec]

    # Fired once the scene is available, with the initial camera.
    on_ready: rx.EventHandler[_location_spec]

    def add_imports(self) -> dict[str, Any]:
        """Imports used by the bridge code.

        Returns:
            The imports.
        """
        return {
            **super().add_imports(),
            "react": [ImportVar(tag="useEffect"), ImportVar(tag="useRef")],
            "resium": [ImportVar(tag="useCesium", install=False)],
            "cesium": [
                cesium_import(name)
                for name in (
                    "Math",
                    "Cartographic",
                    "Cartesian3",
                    "JulianDate",
                    "ScreenSpaceEventHandler",
                    "ScreenSpaceEventType",
                )
            ],
        }

    def add_custom_code(self) -> list[str]:
        """Emit the bridge React component.

        Returns:
            The custom code.
        """
        return [*super().add_custom_code(), _BRIDGE_JS]


cesium_events = CesiumEvents.create


_WIDGET_CONTEXT_JS = r"""
function ReflexResiumWidgetContext({ children }) {
  const ctx = useCesium();
  const widget = ctx.cesiumWidget;
  const value = useMemo(() => {
    if (!widget || ctx.entityCollection || !widget.entities) return ctx;
    return { ...ctx, entityCollection: widget.entities, dataSourceCollection: widget.dataSources };
  }, [ctx, widget]);
  return createElement(CesiumContext.Provider, { value }, children);
}
"""


class CesiumWidgetContext(ResiumComponent):
    """Expose ``CesiumWidget.entities`` / ``dataSources`` to resium children.

    Cesium's ``CesiumWidget`` has had an entity collection and data sources
    for a while, but resium only provides them in ``Viewer``. ``cesium_widget``
    wraps its children with this provider automatically so ``entity``,
    ``custom_data_source``, ``geo_json_data_source``... work inside it too.
    """

    library = None  # type: ignore[assignment]

    tag = "ReflexResiumWidgetContext"

    def add_imports(self) -> dict[str, Any]:
        """Imports for the provider.

        Returns:
            The imports.
        """
        return {
            **super().add_imports(),
            "react": [ImportVar(tag="useMemo"), ImportVar(tag="createElement")],
            "resium": [
                ImportVar(tag="useCesium", install=False),
                ImportVar(tag="CesiumContext", install=False),
            ],
        }

    def add_custom_code(self) -> list[str]:
        """Emit the provider component.

        Returns:
            The custom code.
        """
        return [*super().add_custom_code(), _WIDGET_CONTEXT_JS]


# ---------------------------------------------------------------------------
# Imperative helpers (rx.call_script)
# ---------------------------------------------------------------------------


def _api_call(method: str, *args: Any, callback: Any = None) -> EventSpec:
    """Build an ``rx.call_function`` event calling ``window.reflexResiumApi.<method>``.

    Arguments may be Python values or Vars (state vars, ``rx.foreach`` items):
    the function is created in the render scope, so Vars are captured.
    """
    js_args = [to_js(a) for a in args]
    code = (
        f"(() => (window.reflexResiumApi ? window.reflexResiumApi.{method}("
        f"{', '.join(str(a) for a in js_args)}) : null))"
    )
    function = Var(
        _js_expr=code,
        _var_data=VarData.merge(*(a._get_all_var_data() for a in js_args)),
    )
    if callback is not None:
        return rx.call_function(function, callback=callback)
    return rx.call_function(function)


def fly_to(
    viewer_id: str,
    longitude: float | Var,
    latitude: float | Var,
    height: float = 10000,
    heading: float = 0,
    pitch: float = -90,
    roll: float = 0,
    duration: float | None = None,
) -> EventSpec:
    """Animate the camera to a position (degrees / metres)."""
    return _api_call(
        "flyTo",
        viewer_id,
        {
            "longitude": longitude,
            "latitude": latitude,
            "height": height,
            "heading": heading,
            "pitch": pitch,
            "roll": roll,
            "duration": duration,
        },
    )


def set_view(
    viewer_id: str,
    longitude: float | Var,
    latitude: float | Var,
    height: float = 10000,
    heading: float = 0,
    pitch: float = -90,
    roll: float = 0,
) -> EventSpec:
    """Move the camera instantly."""
    return _api_call(
        "setView",
        viewer_id,
        {
            "longitude": longitude,
            "latitude": latitude,
            "height": height,
            "heading": heading,
            "pitch": pitch,
            "roll": roll,
        },
    )


def fly_home(viewer_id: str, duration: float | None = None) -> EventSpec:
    """Fly the camera to the default home view."""
    return _api_call("flyHome", viewer_id, duration)


def zoom_to_entity(viewer_id: str, entity_id: str | Var, fly: bool = True, duration: float | None = None) -> EventSpec:
    """Zoom/fly to an entity (searched in the viewer and all data sources)."""
    return _api_call("zoomTo", viewer_id, entity_id, fly, duration)


def morph_to(viewer_id: str, mode: str = "3D", duration: float = 2.0) -> EventSpec:
    """Morph the scene to ``"3D"``, ``"2D"`` or ``"COLUMBUS_VIEW"``."""
    return _api_call("morph", viewer_id, mode.upper(), duration)


def set_clock(
    viewer_id: str,
    current_time: str | None = None,
    multiplier: float | None = None,
    should_animate: bool | None = None,
) -> EventSpec:
    """Update the viewer clock (ISO-8601 time, speed multiplier, play/pause)."""
    return _api_call(
        "setClock",
        viewer_id,
        {"current_time": current_time, "multiplier": multiplier, "should_animate": should_animate},
    )


def get_camera(viewer_id: str, callback: Any) -> EventSpec:
    """Read the camera (``{"longitude", "latitude", "height", "heading", "pitch", "roll"}``) into ``callback``."""
    return _api_call("camera", viewer_id, callback=callback)


def screenshot(viewer_id: str, callback: Any) -> EventSpec:
    """Render the scene and send a PNG data URL to ``callback``."""
    return _api_call("screenshot", viewer_id, callback=callback)
