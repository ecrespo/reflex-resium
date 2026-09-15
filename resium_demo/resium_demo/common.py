"""Shared state, layout and viewer helpers for the reflex-resium demo."""

from __future__ import annotations

import reflex as rx

import reflex_resium as rs

NAV_ITEMS: list[tuple[str, str, str]] = [
    ("/", "Entities & state", "map-pin"),
    ("/graphics", "Entity graphics", "shapes"),
    ("/primitives", "Primitives & clouds", "sparkles"),
    ("/data-sources", "Data sources", "database"),
    ("/camera", "Camera & events", "video"),
    ("/scene", "Scene & effects", "sun"),
    ("/layers", "Imagery, models & 3D Tiles", "layers"),
    ("/widget", "CesiumWidget", "app-window"),
]

BASE_MAPS: dict[str, str] = {
    "natural_earth": "Natural Earth II (offline)",
    "osm": "OpenStreetMap",
    "carto_dark": "CARTO Dark Matter",
    "esri": "Esri World Imagery",
}

# A map pin rendered as an SVG data URI (billboard image, no network needed).
PIN_SVG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='32' height='44' viewBox='0 0 32 44'>"
    "<path d='M16 0C7.2 0 0 7.2 0 16c0 12 16 28 16 28s16-16 16-28C32 7.2 24.8 0 16 0z' fill='%23f97316'/>"
    "<circle cx='16' cy='16' r='6' fill='white'/></svg>"
)


class DemoState(rx.State):
    """Base state: a shared event log and the selected base map."""

    log: list[str] = []
    base_map: str = "natural_earth"

    def _push(self, message: str) -> None:
        self.log = [message, *self.log][:40]

    @rx.event
    def clear_log(self):
        self.log = []

    @rx.event
    def set_base_map(self, value: str):
        self.base_map = value
        self._push(f"base map → {value}")


def base_imagery() -> rx.Component:
    """Base map selected in DemoState, rendered as ImageryLayer children."""
    return rx.match(
        DemoState.base_map,
        (
            "osm",
            rs.imagery_layer(
                imagery_provider=rs.Cesium.OpenStreetMapImageryProvider.new(url="https://tile.openstreetmap.org/")
            ),
        ),
        (
            "carto_dark",
            rs.imagery_layer(
                imagery_provider=rs.Cesium.UrlTemplateImageryProvider.new(
                    url="https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
                    credit="© OpenStreetMap contributors © CARTO",
                )
            ),
        ),
        (
            "esri",
            rs.imagery_layer(
                imagery_provider=rs.Cesium.UrlTemplateImageryProvider.new(
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                    credit="Esri, Maxar, Earthstar Geographics",
                    maximum_level=19,
                )
            ),
        ),
        rs.imagery_layer(
            imagery_provider=rs.Cesium.TileMapServiceImageryProvider.fromUrl(
                rs.Cesium.buildModuleUrl("Assets/Textures/NaturalEarthII")
            )
        ),
    )


def demo_viewer(*children: rx.Component, **props) -> rx.Component:
    """A full-size Viewer without Cesium ion dependencies by default."""
    defaults = {
        "full": True,
        "base_layer": False,
        "timeline": False,
        "animation": False,
        "base_layer_picker": False,
        "geocoder": False,
    }
    defaults.update(props)
    return rs.viewer(base_imagery(), *children, **defaults)


def nav() -> rx.Component:
    return rx.vstack(
        *[
            rx.link(
                rx.hstack(rx.icon(icon, size=16), rx.text(label, size="2"), align="center", spacing="2"),
                href=href,
                underline="none",
                color_scheme="gray",
                high_contrast=True,
                width="100%",
                padding="6px 8px",
                border_radius="6px",
                _hover={"background": "var(--gray-a4)"},
            )
            for href, label, icon in NAV_ITEMS
        ],
        spacing="0",
        width="100%",
    )


def section(title: str, *children: rx.Component) -> rx.Component:
    return rx.vstack(
        rx.text(title, size="1", weight="bold", color_scheme="gray", text_transform="uppercase"),
        *children,
        spacing="2",
        width="100%",
        padding_y="8px",
    )


def labeled_slider(label: str, value: rx.Var, on_change, min_: float, max_: float, step: float = 1) -> rx.Component:
    return rx.vstack(
        rx.hstack(rx.text(label, size="2"), rx.spacer(), rx.code(value.to_string()), width="100%"),
        rx.slider(
            value=[value],
            min=min_,
            max=max_,
            step=step,
            on_change=lambda v: on_change(v[0]),
            width="100%",
        ),
        spacing="1",
        width="100%",
    )


def labeled_switch(label: str, checked: rx.Var, on_change) -> rx.Component:
    return rx.hstack(
        rx.text(label, size="2"),
        rx.spacer(),
        rx.switch(checked=checked, on_change=on_change),
        width="100%",
        align="center",
    )


def base_map_select() -> rx.Component:
    return section(
        "Base map",
        rx.select.root(
            rx.select.trigger(width="100%"),
            rx.select.content(*[rx.select.item(label, value=key) for key, label in BASE_MAPS.items()]),
            value=DemoState.base_map,
            on_change=DemoState.set_base_map,
        ),
    )


def event_log() -> rx.Component:
    return section(
        "Event log",
        rx.box(
            rx.foreach(DemoState.log, lambda line: rx.text(line, size="1", font_family="monospace")),
            max_height="180px",
            overflow_y="auto",
            width="100%",
            padding="8px",
            border_radius="6px",
            background="var(--gray-a3)",
        ),
        rx.button("Clear log", size="1", variant="soft", on_click=DemoState.clear_log),
    )


def page_shell(title: str, description: str, controls: rx.Component, viewer: rx.Component) -> rx.Component:
    return rx.flex(
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("globe", size=22),
                    rx.heading("reflex-resium", size="5"),
                    rx.badge(f"resium {rs.RESIUM_VERSION}", variant="soft"),
                    align="center",
                ),
                nav(),
                rx.divider(),
                rx.heading(title, size="4"),
                rx.text(description, size="2", color_scheme="gray"),
                controls,
                rx.divider(),
                event_log(),
                spacing="3",
                width="100%",
            ),
            width=["100%", "100%", "360px"],
            min_width=["auto", "auto", "360px"],
            height=["auto", "auto", "100vh"],
            overflow_y="auto",
            padding="16px",
            border_right="1px solid var(--gray-a5)",
        ),
        rx.box(viewer, position="relative", flex="1", height=["70vh", "70vh", "100vh"], overflow="hidden"),
        direction=rx.breakpoints(initial="column-reverse", md="row"),
        width="100%",
    )
