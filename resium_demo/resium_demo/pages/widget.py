"""CesiumWidget: the lightweight root component (no widgets, engine only)."""

from __future__ import annotations

import reflex as rx

import reflex_resium as rs

from ..common import DemoState, page_shell, section

C = rs.Cesium


class WidgetState(DemoState):
    camera: dict = {}
    spin: bool = True

    @rx.event
    def on_camera(self, info: dict):
        self.camera = {k: round(v, 3) for k, v in info.items() if isinstance(v, (int, float))}

    @rx.event
    def toggle_spin(self, value: bool):
        self.spin = value


def widget_page() -> rx.Component:
    return page_shell(
        "CesiumWidget",
        "CesiumWidget is the minimal root: no InfoBox, timeline or toolbars. Everything "
        "else (entities, imagery, camera, events) works the same.",
        rx.vstack(
            section(
                "Controls",
                rx.hstack(
                    rx.text("Animate clock", size="2"),
                    rx.spacer(),
                    rx.switch(checked=WidgetState.spin, on_change=WidgetState.toggle_spin),
                    width="100%",
                ),
                rx.button("Fly to Caracas", size="1", on_click=rs.fly_to("widget", -66.9, 10.48, 400_000, duration=2)),
                rx.button("Home", size="1", variant="outline", on_click=rs.fly_home("widget", 2)),
            ),
            section(
                "Camera",
                rx.foreach(
                    WidgetState.camera,
                    lambda kv: rx.hstack(
                        rx.text(kv[0], size="1"), rx.spacer(), rx.code(kv[1].to_string(), size="1"), width="100%"
                    ),
                ),
            ),
            width="100%",
        ),
        rs.cesium_widget(
            rs.imagery_layer(
                imagery_provider=C.TileMapServiceImageryProvider.fromUrl(
                    C.buildModuleUrl("Assets/Textures/NaturalEarthII")
                )
            ),
            rs.globe(enable_lighting=True),
            rs.clock(multiplier=4000, should_animate=WidgetState.spin),
            rs.entity(
                name="Caracas",
                position=rs.cartesian3(-66.9036, 10.4806, 0),
                point={"pixelSize": 12, "color": C.Color.fromCssColorString("#facc15")},
                label={"text": "Caracas", "font": "14px sans-serif", "pixelOffset": rs.cartesian2(0, -18)},
            ),
            rs.cesium_events(
                viewer_id="widget", on_camera_change=WidgetState.on_camera, on_ready=WidgetState.on_camera
            ),
            full=True,
            base_layer=False,
        ),
    )
