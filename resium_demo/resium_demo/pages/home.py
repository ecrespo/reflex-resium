"""Entities driven by Reflex state: foreach, selection, descriptions, clicks."""

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

CITIES = [
    {
        "id": "caracas",
        "name": "Caracas",
        "country": "Venezuela",
        "lon": -66.9036,
        "lat": 10.4806,
        "population": 2245744,
        "color": "#facc15",
    },
    {
        "id": "barcelona",
        "name": "Barcelona",
        "country": "Spain",
        "lon": 2.1734,
        "lat": 41.3851,
        "population": 1636732,
        "color": "#f43f5e",
    },
    {
        "id": "madrid",
        "name": "Madrid",
        "country": "Spain",
        "lon": -3.7038,
        "lat": 40.4168,
        "population": 3305408,
        "color": "#fb923c",
    },
    {
        "id": "tokyo",
        "name": "Tokyo",
        "country": "Japan",
        "lon": 139.767052,
        "lat": 35.681167,
        "population": 13960000,
        "color": "#22d3ee",
    },
    {
        "id": "new-york",
        "name": "New York",
        "country": "USA",
        "lon": -74.0060,
        "lat": 40.7128,
        "population": 8336817,
        "color": "#a78bfa",
    },
    {
        "id": "buenos-aires",
        "name": "Buenos Aires",
        "country": "Argentina",
        "lon": -58.3816,
        "lat": -34.6037,
        "population": 3120612,
        "color": "#34d399",
    },
    {
        "id": "cape-town",
        "name": "Cape Town",
        "country": "South Africa",
        "lon": 18.4241,
        "lat": -33.9249,
        "population": 4772846,
        "color": "#60a5fa",
    },
    {
        "id": "sydney",
        "name": "Sydney",
        "country": "Australia",
        "lon": 151.2093,
        "lat": -33.8688,
        "population": 5312163,
        "color": "#f472b6",
    },
]


class EntitiesState(DemoState):
    cities: list[dict] = CITIES
    selected_id: str = ""
    pins: list[dict] = []
    point_size: float = 14
    show_labels: bool = True
    cursor: str = "—"

    @rx.var
    def selected_city(self) -> dict:
        return next((c for c in self.cities if c["id"] == self.selected_id), {})

    @rx.event
    def set_point_size(self, value: float):
        self.point_size = value

    @rx.event
    def set_show_labels(self, value: bool):
        self.show_labels = value

    @rx.event
    def select(self, city_id: str):
        self.selected_id = city_id

    @rx.event
    def on_selected_entity_change(self, entity: dict | None):
        self.selected_id = (entity or {}).get("id") or ""
        self._push(f"selected entity → {self.selected_id or 'none'}")

    @rx.event
    def on_entity_click(self, movement: dict, target: dict):
        self._push(f"Entity.on_click {target.get('name') if target else None} at {movement.get('position')}")

    @rx.event
    def on_right_click(self, info: dict):
        if info.get("longitude") is None:
            return
        pin = {
            "id": f"pin-{len(self.pins) + 1}",
            "lon": info["longitude"],
            "lat": info["latitude"],
            "label": f"Pin {len(self.pins) + 1}",
        }
        self.pins = [*self.pins, pin]
        self._push(f"pin dropped at {info['latitude']:.3f}, {info['longitude']:.3f}")

    @rx.event
    def clear_pins(self):
        self.pins = []

    @rx.event
    def on_mouse_move(self, info: dict):
        if info.get("latitude") is None:
            self.cursor = "—"
        else:
            self.cursor = f"{info['latitude']:.4f}, {info['longitude']:.4f}"


def city_entity(city: rx.Var) -> rx.Component:
    return rs.entity(
        rs.point_graphics(
            pixel_size=EntitiesState.point_size,
            color=rs.color(city["color"]),
            outline_color=rs.Cesium.Color.WHITE,
            outline_width=2,
        ),
        rx.cond(
            EntitiesState.show_labels,
            rs.label_graphics(
                text=city["name"],
                font="bold 14px sans-serif",
                fill_color=rs.Cesium.Color.WHITE,
                outline_color=rs.Cesium.Color.BLACK,
                outline_width=3,
                cesium_style=rs.Cesium.LabelStyle.FILL_AND_OUTLINE,
                vertical_origin=rs.Cesium.VerticalOrigin.BOTTOM,
                pixel_offset=rs.cartesian2(0, -14),
            ),
        ),
        rs.entity_description(
            # The InfoBox is an iframe: Emotion/Radix CSS classes don't reach it,
            # so use plain elements with inline styles (custom_attrs).
            rx.el.div(
                rx.el.h2(city["name"], custom_attrs={"style": {"margin": "0 0 8px", "color": city["color"]}}),
                rx.el.p("Country: ", rx.el.strong(city["country"])),
                rx.el.p("Population: ", rx.el.strong(city["population"].to_string())),
                rx.el.p("Rendered with Reflex components inside Cesium's InfoBox."),
                custom_attrs={
                    "style": {
                        "padding": "8px",
                        "color": "#e5e7eb",
                        "background": "#111827",
                        "fontFamily": "sans-serif",
                        "fontSize": "14px",
                    }
                },
            ),
        ),
        id=city["id"],
        name=city["name"],
        position=rs.cartesian3(city["lon"], city["lat"], 0),
        selected=EntitiesState.selected_id == city["id"],
        on_click=EntitiesState.on_entity_click,
    )


def pin_entity(pin: rx.Var) -> rx.Component:
    return rs.entity(
        rs.billboard_graphics(
            image=PIN_SVG,
            vertical_origin=rs.Cesium.VerticalOrigin.BOTTOM,
            scale=1.0,
        ),
        id=pin["id"],
        name=pin["label"],
        description="Dropped with a right click (CesiumEvents.on_right_click).",
        position=rs.cartesian3(pin["lon"], pin["lat"], 0),
    )


def controls() -> rx.Component:
    return rx.vstack(
        base_map_select(),
        section(
            "Style (state → props)",
            labeled_slider("Point size", EntitiesState.point_size, EntitiesState.set_point_size, 4, 40),
            labeled_switch("Labels", EntitiesState.show_labels, EntitiesState.set_show_labels),
        ),
        section(
            "Cities (rx.foreach → Entity)",
            rx.foreach(
                EntitiesState.cities,
                lambda c: rx.hstack(
                    rx.box(width="10px", height="10px", border_radius="50%", background=c["color"]),
                    rx.text(
                        c["name"], size="2", weight=rx.cond(EntitiesState.selected_id == c["id"], "bold", "regular")
                    ),
                    rx.spacer(),
                    rx.button("Select", size="1", variant="soft", on_click=EntitiesState.select(c["id"])),
                    rx.button("Fly", size="1", on_click=rs.fly_to("home", c["lon"], c["lat"], 1_500_000, duration=2)),
                    width="100%",
                    align="center",
                ),
            ),
            rx.button("Fly home", size="1", variant="outline", on_click=rs.fly_home("home", 2)),
        ),
        rx.cond(
            EntitiesState.selected_id != "",
            section(
                "Selected (two-way with Viewer.selectedEntity)",
                rx.card(
                    rx.text(EntitiesState.selected_city["name"], weight="bold"),
                    rx.text(EntitiesState.selected_city["country"], size="2"),
                    rx.button(
                        "Zoom to entity",
                        size="1",
                        margin_top="6px",
                        on_click=rs.zoom_to_entity("home", EntitiesState.selected_id),
                    ),
                    width="100%",
                ),
            ),
        ),
        section(
            "Geographic events (CesiumEvents)",
            rx.text("Cursor: ", rx.code(EntitiesState.cursor), size="2"),
            rx.text("Right-click the globe to drop a pin.", size="2", color_scheme="gray"),
            rx.hstack(
                rx.badge(EntitiesState.pins.length().to_string() + " pins"),
                rx.button("Clear pins", size="1", variant="soft", on_click=EntitiesState.clear_pins),
                align="center",
            ),
        ),
        width="100%",
    )


def entities_page() -> rx.Component:
    return page_shell(
        "Entities & state",
        "Entities rendered from a list in Reflex state, with rich InfoBox descriptions, "
        "selection synced both ways and geographic mouse events sent to the backend.",
        controls(),
        demo_viewer(
            rs.camera_fly_to(destination=rs.cartesian3(-30, 20, 22_000_000), duration=0, once=True),
            rx.foreach(EntitiesState.cities, city_entity),
            rx.foreach(EntitiesState.pins, pin_entity),
            rs.cesium_events(
                viewer_id="home",
                on_selected_entity_change=EntitiesState.on_selected_entity_change,
                on_right_click=EntitiesState.on_right_click,
                on_mouse_move=EntitiesState.on_mouse_move,
                mouse_move_throttle=150,
            ),
        ),
    )
