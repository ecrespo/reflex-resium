"""Every Entity *Graphics component, styled live from Reflex state."""

from __future__ import annotations

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
COLORS = ["#22d3ee", "#f97316", "#a3e635", "#e879f9", "#facc15", "#f43f5e"]


class GraphicsState(DemoState):
    color: str = "#22d3ee"
    alpha: float = 0.8
    extruded_height: float = 250_000
    outline: bool = True
    rotation: float = 0
    show_labels: bool = True

    @rx.var
    def rotation_radians(self) -> float:
        return self.rotation * 3.141592653589793 / 180

    @rx.event
    def set_color(self, value: str):
        self.color = value

    @rx.event
    def set_alpha(self, value: float):
        self.alpha = value

    @rx.event
    def set_extruded_height(self, value: float):
        self.extruded_height = value

    @rx.event
    def set_outline(self, value: bool):
        self.outline = value

    @rx.event
    def set_rotation(self, value: float):
        self.rotation = value

    @rx.event
    def set_show_labels(self, value: bool):
        self.show_labels = value

    @rx.event
    def clicked(self, movement: dict, target: dict):
        self._push(f"clicked {target.get('name') if target else '?'}")


def material():
    return rs.color(GraphicsState.color, GraphicsState.alpha)


def shape(name: str, lon: float, lat: float, *graphics: rx.Component, height: float = 0, **props) -> rx.Component:
    return rs.entity(
        *graphics,
        rx.cond(
            GraphicsState.show_labels,
            rs.label_graphics(
                text=name,
                font="13px sans-serif",
                fill_color=C.Color.WHITE,
                show_background=True,
                background_color=C.Color.BLACK.withAlpha(0.6),
                vertical_origin=C.VerticalOrigin.BOTTOM,
                pixel_offset=rs.cartesian2(0, -12),
                disable_depth_test_distance=1e10,
            ),
        ),
        name=name,
        position=rs.cartesian3(lon, lat, height),
        on_click=GraphicsState.clicked,
        **props,
    )


def graphics_entities() -> list[rx.Component]:
    common = {"outline": GraphicsState.outline, "outline_color": C.Color.WHITE}
    return [
        shape(
            "BoxGraphics",
            -110,
            45,
            rs.box_graphics(
                dimensions=C.Cartesian3.new(400_000, 300_000, GraphicsState.extruded_height + 1),
                material=material(),
                **common,
            ),
            height=GraphicsState.extruded_height / 2,
        ),
        shape(
            "CylinderGraphics",
            -100,
            45,
            rs.cylinder_graphics(
                length=GraphicsState.extruded_height + 1,
                top_radius=0,
                bottom_radius=200_000,
                material=material(),
                **common,
            ),
            height=GraphicsState.extruded_height / 2,
        ),
        shape(
            "EllipsoidGraphics",
            -90,
            45,
            rs.ellipsoid_graphics(radii=C.Cartesian3.new(200_000, 200_000, 300_000), material=material(), **common),
            height=300_000,
        ),
        shape(
            "EllipseGraphics",
            -80,
            45,
            rs.ellipse_graphics(
                semi_major_axis=300_000,
                semi_minor_axis=150_000,
                rotation=GraphicsState.rotation_radians,
                extruded_height=GraphicsState.extruded_height,
                material=material(),
                **common,
            ),
        ),
        shape(
            "PolygonGraphics",
            -110,
            35,
            rs.polygon_graphics(
                hierarchy=rs.cartesian3_array([[-113, 32], [-107, 32], [-106, 37], [-110, 39], [-114, 36]]),
                extruded_height=GraphicsState.extruded_height,
                material=material(),
                **common,
            ),
            height=GraphicsState.extruded_height,
        ),
        shape(
            "RectangleGraphics",
            -100,
            35,
            rs.rectangle_graphics(
                coordinates=rs.rectangle_from_degrees(-103, 32, -97, 38),
                rotation=GraphicsState.rotation_radians,
                extruded_height=GraphicsState.extruded_height,
                material=C.StripeMaterialProperty.new(
                    even_color=C.Color.WHITE.withAlpha(0.6), odd_color=material(), repeat=8
                ),
                **common,
            ),
            height=GraphicsState.extruded_height,
        ),
        shape(
            "WallGraphics",
            -90,
            35,
            rs.wall_graphics(
                positions=rs.cartesian3_array_heights([[-93, 33, 300_000], [-90, 37, 300_000], [-87, 33, 300_000]]),
                minimum_heights=[0, 0, 0],
                material=material(),
                **common,
            ),
            height=320_000,
        ),
        shape(
            "CorridorGraphics",
            -80,
            35,
            rs.corridor_graphics(
                positions=rs.cartesian3_array([[-84, 32], [-80, 36], [-76, 33]]),
                width=150_000,
                extruded_height=GraphicsState.extruded_height / 2,
                corner_type=C.CornerType.ROUNDED,
                material=material(),
                **common,
            ),
            height=GraphicsState.extruded_height / 2,
        ),
        shape(
            "PolylineGraphics",
            -110,
            25,
            rs.polyline_graphics(
                positions=rs.cartesian3_array([[-115, 22], [-110, 28], [-105, 22]]),
                width=10,
                material=C.PolylineGlowMaterialProperty.new(glow_power=0.25, color=material()),
            ),
        ),
        shape(
            "PolylineVolumeGraphics",
            -100,
            25,
            rs.polyline_volume_graphics(
                positions=rs.cartesian3_array_heights([[-104, 22, 100_000], [-100, 27, 100_000], [-96, 22, 100_000]]),
                shape=rs.js(
                    "Array.from({length: 24}, (_, i) => new Cesium_Cartesian2(60000 * Math.cos(i / 24 * 2 * Math.PI), 60000 * Math.sin(i / 24 * 2 * Math.PI)))",
                    "Cartesian2",
                    deps=[],
                ),
                material=material(),
                **common,
            ),
            height=180_000,
        ),
        shape(
            "PlaneGraphics",
            -90,
            25,
            rs.plane_graphics(
                plane=C.Plane.new(C.Cartesian3.UNIT_Z, 0),
                dimensions=rs.cartesian2(400_000, 300_000),
                material=material(),
                **common,
            ),
            height=150_000,
        ),
        shape(
            "PointGraphics",
            -80,
            25,
            rs.point_graphics(pixel_size=24, color=material(), outline_color=C.Color.WHITE, outline_width=2),
        ),
        shape(
            "BillboardGraphics",
            -70,
            25,
            rs.billboard_graphics(
                image=PIN_SVG, scale=1.5, vertical_origin=C.VerticalOrigin.BOTTOM, color=C.Color.WHITE
            ),
        ),
        shape(
            "Entity props (dict)",
            -70,
            40,
            # Graphics can also be passed as plain option objects on Entity.
            point={"pixelSize": 18, "color": C.Color.fromCssColorString("#facc15")},
            ellipse={"semiMajorAxis": 200_000, "semiMinorAxis": 200_000, "material": C.Color.YELLOW.withAlpha(0.25)},
        ),
    ]


def controls() -> rx.Component:
    return rx.vstack(
        base_map_select(),
        section(
            "Material",
            rx.hstack(
                *[
                    rx.box(
                        width="28px",
                        height="28px",
                        border_radius="6px",
                        background=c,
                        cursor="pointer",
                        border=rx.cond(GraphicsState.color == c, "2px solid white", "2px solid transparent"),
                        on_click=GraphicsState.set_color(c),
                    )
                    for c in COLORS
                ],
                spacing="2",
            ),
            labeled_slider("Alpha", GraphicsState.alpha, GraphicsState.set_alpha, 0.1, 1, 0.05),
            labeled_switch("Outline", GraphicsState.outline, GraphicsState.set_outline),
            labeled_switch("Labels", GraphicsState.show_labels, GraphicsState.set_show_labels),
        ),
        section(
            "Geometry",
            labeled_slider(
                "Extruded height (m)",
                GraphicsState.extruded_height,
                GraphicsState.set_extruded_height,
                0,
                800_000,
                10_000,
            ),
            labeled_slider("Rotation (°)", GraphicsState.rotation, GraphicsState.set_rotation, 0, 360, 5),
        ),
        width="100%",
    )


def graphics_page() -> rx.Component:
    return page_shell(
        "Entity graphics",
        "Box, Cylinder, Ellipsoid, Ellipse, Polygon, Rectangle, Wall, Corridor, Polyline, "
        "PolylineVolume, Plane, Point, Billboard and Label graphics. Every slider updates "
        "Cesium properties in place (no re-creation).",
        controls(),
        demo_viewer(
            rs.camera_fly_to(
                destination=rs.cartesian3(-92, 5, 5_500_000),
                orientation=rs.camera_orientation(0, -60),
                duration=0,
                once=True,
            ),
            *graphics_entities(),
            rs.cesium_events(viewer_id="graphics"),
        ),
    )
