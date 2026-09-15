"""Low-level primitives: point/label/billboard/polyline collections, Primitive, clouds."""

from __future__ import annotations

import random

import reflex as rx

import reflex_resium as rs

from ..common import (
    PIN_SVG,
    DemoState,
    base_map_select,
    demo_viewer,
    labeled_slider,
    labeled_switch,
    page_shell,
    section,
)

C = rs.Cesium


def _random_points(count: int, seed: int) -> list[dict]:
    # Deterministic demo data, not used for security.
    rng = random.Random(seed)  # noqa: S311  # nosec B311
    return [
        {
            "id": f"pt-{i}",
            "lon": rng.uniform(-20, 40),
            "lat": rng.uniform(-35, 35),
            "color": rng.choice(["#22d3ee", "#f97316", "#a3e635", "#e879f9", "#facc15"]),
        }
        for i in range(count)
    ]


class PrimitivesState(DemoState):
    count: int = 150
    seed: int = 7
    points: list[dict] = _random_points(150, 7)
    pixel_size: float = 8
    show_points: bool = True
    show_labels: bool = True
    show_billboards: bool = True
    show_polylines: bool = True
    show_primitive: bool = True
    cloud_scale: float = 1.0

    @rx.event
    def set_count(self, value: float):
        self.count = int(value)
        self.points = _random_points(self.count, self.seed)

    @rx.event
    def reshuffle(self):
        self.seed += 1
        self.points = _random_points(self.count, self.seed)
        self._push(f"regenerated {self.count} PointPrimitives")

    @rx.event
    def set_pixel_size(self, value: float):
        self.pixel_size = value

    @rx.event
    def set_show_points(self, value: bool):
        self.show_points = value

    @rx.event
    def set_show_labels(self, value: bool):
        self.show_labels = value

    @rx.event
    def set_show_billboards(self, value: bool):
        self.show_billboards = value

    @rx.event
    def set_show_polylines(self, value: bool):
        self.show_polylines = value

    @rx.event
    def set_show_primitive(self, value: bool):
        self.show_primitive = value

    @rx.event
    def set_cloud_scale(self, value: float):
        self.cloud_scale = value

    @rx.event
    def point_clicked(self, movement: dict, target: dict):
        self._push(f"PointPrimitive click id={target.get('id') if target else None}")

    @rx.event
    def primitive_ready(self, info: dict):
        self._push("Primitive.on_ready")


CLOUD_POSITIONS = [
    (-122.0, 46.0, 1500),
    (-122.01, 46.005, 1600),
    (-121.99, 45.995, 1450),
    (-122.02, 45.99, 1700),
    (-121.98, 46.01, 1550),
]


def controls() -> rx.Component:
    return rx.vstack(
        base_map_select(),
        section(
            "PointPrimitiveCollection",
            labeled_slider("Points", PrimitivesState.count, PrimitivesState.set_count, 10, 1000, 10),
            labeled_slider("Pixel size", PrimitivesState.pixel_size, PrimitivesState.set_pixel_size, 2, 24),
            rx.button("Regenerate", size="1", variant="soft", on_click=PrimitivesState.reshuffle),
            labeled_switch("Show points", PrimitivesState.show_points, PrimitivesState.set_show_points),
        ),
        section(
            "Other collections",
            labeled_switch("LabelCollection", PrimitivesState.show_labels, PrimitivesState.set_show_labels),
            labeled_switch("BillboardCollection", PrimitivesState.show_billboards, PrimitivesState.set_show_billboards),
            labeled_switch("PolylineCollection", PrimitivesState.show_polylines, PrimitivesState.set_show_polylines),
            labeled_switch(
                "Primitive (GeometryInstance)", PrimitivesState.show_primitive, PrimitivesState.set_show_primitive
            ),
        ),
        section(
            "CloudCollection / CumulusCloud",
            labeled_slider("Cloud scale", PrimitivesState.cloud_scale, PrimitivesState.set_cloud_scale, 0.3, 2.5, 0.1),
            rx.button(
                "Fly to the clouds",
                size="1",
                on_click=rs.fly_to("primitives", -122.0, 45.93, 1800, heading=0, pitch=5, duration=3),
            ),
            rx.button(
                "Back to overview",
                size="1",
                variant="outline",
                on_click=rs.fly_to("primitives", 10, 0, 12_000_000, duration=2),
            ),
        ),
        width="100%",
    )


def primitives_page() -> rx.Component:
    return page_shell(
        "Primitives & clouds",
        "Collections render thousands of objects efficiently. The Primitive uses raw Cesium "
        "geometry built with the rs.Cesium bridge.",
        controls(),
        demo_viewer(
            rs.camera_fly_to(destination=rs.cartesian3(10, 0, 12_000_000), duration=0, once=True),
            rs.point_primitive_collection(
                rx.foreach(
                    PrimitivesState.points,
                    lambda p: rs.point_primitive(
                        id=p["id"],
                        position=rs.cartesian3(p["lon"], p["lat"], 0),
                        color=rs.color(p["color"]),
                        pixel_size=PrimitivesState.pixel_size,
                        outline_color=C.Color.BLACK,
                        outline_width=1,
                        on_click=PrimitivesState.point_clicked,
                    ),
                ),
                show=PrimitivesState.show_points,
            ),
            rs.label_collection(
                rs.label(
                    position=rs.cartesian3(-75, 45, 0),
                    text="LabelCollection",
                    font="20px sans-serif",
                    fill_color=C.Color.WHITE,
                ),
                rs.label(
                    position=rs.cartesian3(-75, 40, 0),
                    text="Label with background",
                    font="16px sans-serif",
                    show_background=True,
                    background_color=C.Color.fromCssColorString("#0e7490"),
                ),
                show=PrimitivesState.show_labels,
            ),
            rs.billboard_collection(
                rs.billboard(
                    position=rs.cartesian3(-60, 45, 0),
                    image=PIN_SVG,
                    scale=1.2,
                    vertical_origin=C.VerticalOrigin.BOTTOM,
                ),
                rs.billboard(
                    position=rs.cartesian3(-55, 40, 0),
                    image=PIN_SVG,
                    scale=2.0,
                    color=C.Color.LIME,
                    vertical_origin=C.VerticalOrigin.BOTTOM,
                ),
                show=PrimitivesState.show_billboards,
            ),
            rx.cond(
                PrimitivesState.show_polylines,
                rs.polyline_collection(
                    rs.polyline(
                        positions=rs.cartesian3_array([[-80, 30], [-60, 30], [-40, 20], [-20, 25]]),
                        width=4,
                        material=C.Material.fromType("Color", {"color": C.Color.fromCssColorString("#f97316")}),
                    ),
                    rs.polyline(
                        positions=rs.cartesian3_array([[-80, 25], [-20, 20]]),
                        width=8,
                        material=C.Material.fromType("PolylineArrow", {"color": C.Color.fromCssColorString("#a3e635")}),
                    ),
                ),
            ),
            rs.primitive(
                geometry_instances=C.GeometryInstance.new(
                    geometry=C.RectangleGeometry.new(
                        rectangle=rs.rectangle_from_degrees(-110, -40, -70, -15),
                        vertex_format=C.EllipsoidSurfaceAppearance.VERTEX_FORMAT,
                    )
                ),
                appearance=C.EllipsoidSurfaceAppearance.new(
                    aboveGround=False,
                    material=C.Material.fromType("Checkerboard", {"repeat": rs.cartesian2(20, 10)}),
                ),
                show=PrimitivesState.show_primitive,
                on_ready=PrimitivesState.primitive_ready,
            ),
            rs.cloud_collection(
                *[
                    rs.cumulus_cloud(
                        position=rs.cartesian3(lon, lat, h),
                        scale=rs.cartesian2(PrimitivesState.cloud_scale * 250, PrimitivesState.cloud_scale * 80),
                        maximum_size=C.Cartesian3.new(50, 15, 13),
                        slice=0.36,
                    )
                    for lon, lat, h in CLOUD_POSITIONS
                ],
                noise_detail=16.0,
            ),
            rs.cesium_events(viewer_id="primitives"),
        ),
    )
