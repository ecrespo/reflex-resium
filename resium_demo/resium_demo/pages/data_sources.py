"""GeoJSON, KML, CZML and CustomDataSource (with clustering)."""

from __future__ import annotations

import math
import random

import reflex as rx

import reflex_resium as rs

from ..common import DemoState, base_map_select, demo_viewer, labeled_switch, page_shell, section

C = rs.Cesium

EPOCH = "2026-09-15T00:00:00Z"


def satellite_czml(
    name: str, inclination: float, raan: float, color: list[int], period_s: int = 5400, altitude: float = 700_000
) -> dict:
    """A simple circular orbit sampled every 60 s (ground track rotates with Earth)."""
    samples: list[float] = []
    for t in range(0, period_s * 2 + 1, 60):
        u = 2 * math.pi * t / period_s
        inc = math.radians(inclination)
        lat = math.degrees(math.asin(math.sin(inc) * math.sin(u)))
        lon = raan + math.degrees(math.atan2(math.cos(inc) * math.sin(u), math.cos(u))) - 360 * t / 86164
        lon = (lon + 540) % 360 - 180
        samples += [t, lon, lat, altitude]
    return {
        "id": name.lower().replace(" ", "-"),
        "name": name,
        "description": f"<p>{name}: inclination {inclination}°, altitude {altitude / 1000:.0f} km.</p>",
        "availability": f"{EPOCH}/2026-09-15T03:00:00Z",
        "position": {
            "epoch": EPOCH,
            "cartographicDegrees": samples,
            "interpolationAlgorithm": "LAGRANGE",
            "interpolationDegree": 3,
        },
        "point": {
            "pixelSize": 10,
            "color": {"rgba": color},
            "outlineColor": {"rgba": [255, 255, 255, 255]},
            "outlineWidth": 2,
        },
        "label": {
            "text": name,
            "font": "13px sans-serif",
            "pixelOffset": {"cartesian2": [0, -18]},
            "fillColor": {"rgba": color},
        },
        "path": {
            "material": {"solidColor": {"color": {"rgba": color}}},
            "width": 2,
            "leadTime": 2700,
            "trailTime": 2700,
            "resolution": 120,
        },
    }


CZML = [
    {
        "id": "document",
        "name": "Demo satellites",
        "version": "1.0",
        "clock": {
            "interval": f"{EPOCH}/2026-09-15T03:00:00Z",
            "currentTime": EPOCH,
            "multiplier": 60,
            "range": "LOOP_STOP",
            "step": "SYSTEM_CLOCK_MULTIPLIER",
        },
    },
    satellite_czml("Sat Alpha", 51.6, 0, [34, 211, 238, 255]),
    satellite_czml("Sat Beta", 98.2, 120, [249, 115, 22, 255], period_s=5900, altitude=800_000),
    satellite_czml("Sat Gamma", 28.5, 240, [163, 230, 53, 255], period_s=5200, altitude=550_000),
]

# Deterministic demo data, not used for security.
_rng = random.Random(42)  # noqa: S311  # nosec B311
CLUSTER_POINTS = [{"id": f"c{i}", "lon": _rng.gauss(10, 8), "lat": _rng.gauss(48, 6)} for i in range(400)]

INLINE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"name": "Inline GeoJSON polygon", "source": "Python dict in state"},
            "geometry": {"type": "Polygon", "coordinates": [[[-75, 0], [-60, 0], [-60, 12], [-75, 12], [-75, 0]]]},
        },
        {
            "type": "Feature",
            "properties": {"name": "Inline GeoJSON line"},
            "geometry": {"type": "LineString", "coordinates": [[-80, -5], [-70, -15], [-55, -10]]},
        },
    ],
}


class DataSourcesState(DemoState):
    show_geojson: bool = True
    show_inline: bool = True
    show_kml: bool = True
    show_czml: bool = True
    show_custom: bool = True
    clustering: bool = True
    inline_geojson: dict = INLINE_GEOJSON
    fill: str = "#22d3ee"
    loaded: dict[str, int] = {}

    @rx.event
    def set_show_geojson(self, v: bool):
        self.show_geojson = v

    @rx.event
    def set_show_inline(self, v: bool):
        self.show_inline = v

    @rx.event
    def set_show_kml(self, v: bool):
        self.show_kml = v

    @rx.event
    def set_show_czml(self, v: bool):
        self.show_czml = v

    @rx.event
    def set_show_custom(self, v: bool):
        self.show_custom = v

    @rx.event
    def set_clustering(self, v: bool):
        self.clustering = v

    @rx.event
    def cycle_fill(self):
        palette = ["#22d3ee", "#f97316", "#a3e635", "#e879f9"]
        self.fill = palette[(palette.index(self.fill) + 1) % len(palette)]

    @rx.event
    def on_load(self, source: dict):
        name = source.get("name") or "data source"
        self.loaded = {**self.loaded, name: source.get("entity_count", 0)}
        self._push(f"on_load {name}: {source.get('entity_count')} entities")

    @rx.event
    def on_error(self, source: dict, message: str):
        self._push(f"on_error {message}")

    @rx.event
    def feature_clicked(self, movement: dict, target: dict):
        if target:
            self._push(f"clicked {target.get('name')} {target.get('properties')}")


def controls() -> rx.Component:
    return rx.vstack(
        base_map_select(),
        section(
            "Sources",
            labeled_switch("GeoJsonDataSource (URL)", DataSourcesState.show_geojson, DataSourcesState.set_show_geojson),
            labeled_switch(
                "GeoJsonDataSource (inline dict)", DataSourcesState.show_inline, DataSourcesState.set_show_inline
            ),
            rx.button("Cycle inline fill color", size="1", variant="soft", on_click=DataSourcesState.cycle_fill),
            labeled_switch("KmlDataSource", DataSourcesState.show_kml, DataSourcesState.set_show_kml),
            labeled_switch("CzmlDataSource (animated)", DataSourcesState.show_czml, DataSourcesState.set_show_czml),
            labeled_switch("CustomDataSource", DataSourcesState.show_custom, DataSourcesState.set_show_custom),
            labeled_switch("EntityCluster clustering", DataSourcesState.clustering, DataSourcesState.set_clustering),
        ),
        section(
            "Loaded (on_load events)",
            rx.foreach(
                DataSourcesState.loaded,
                lambda item: rx.hstack(
                    rx.text(item[0], size="2"), rx.spacer(), rx.badge(item[1].to_string()), width="100%"
                ),
            ),
        ),
        section(
            "Go to",
            rx.hstack(
                rx.button(
                    "Barcelona KML", size="1", on_click=rs.fly_to("data", 2.17, 41.33, 9000, pitch=-45, duration=2)
                ),
                rx.button(
                    "Europe cluster", size="1", on_click=rs.fly_to("data", 10, 40, 4_500_000, pitch=-80, duration=2)
                ),
                rx.button(
                    "World", size="1", variant="outline", on_click=rs.fly_to("data", -20, 10, 25_000_000, duration=2)
                ),
                wrap="wrap",
            ),
        ),
        width="100%",
    )


def data_sources_page() -> rx.Component:
    return page_shell(
        "Data sources",
        "GeoJSON from an asset URL and from a Python dict, KML, time-dynamic CZML "
        "(satellites with paths driving the clock) and a clustered CustomDataSource.",
        controls(),
        demo_viewer(
            rs.camera_fly_to(destination=rs.cartesian3(-20, 10, 25_000_000), duration=0, once=True),
            rs.geo_json_data_source(
                data=rx.asset("data/volcanoes.geojson"),
                name="Volcanoes (GeoJSON URL)",
                marker_color=C.Color.fromCssColorString("#f43f5e"),
                marker_symbol="volcano",
                marker_size=40,
                show=DataSourcesState.show_geojson,
                on_load=DataSourcesState.on_load,
                on_error=DataSourcesState.on_error,
                on_click=DataSourcesState.feature_clicked,
            ),
            rs.geo_json_data_source(
                data=DataSourcesState.inline_geojson,
                name="Inline GeoJSON",
                stroke=C.Color.WHITE,
                stroke_width=3,
                fill=rs.color(DataSourcesState.fill, 0.4),
                show=DataSourcesState.show_inline,
                on_load=DataSourcesState.on_load,
                on_click=DataSourcesState.feature_clicked,
            ),
            rs.kml_data_source(
                data=rx.asset("data/barcelona.kml"),
                clamp_to_ground=True,
                show=DataSourcesState.show_kml,
                on_load=DataSourcesState.on_load,
                on_error=DataSourcesState.on_error,
                on_click=DataSourcesState.feature_clicked,
            ),
            rx.cond(
                DataSourcesState.show_czml,
                rs.czml_data_source(
                    data=CZML, on_load=DataSourcesState.on_load, on_click=DataSourcesState.feature_clicked
                ),
            ),
            rs.custom_data_source(
                rx.foreach(
                    CLUSTER_POINTS,
                    lambda p: rs.entity(
                        id=p["id"],
                        position=rs.cartesian3(p["lon"], p["lat"], 0),
                        point={"pixelSize": 8, "color": C.Color.fromCssColorString("#facc15")},
                    ),
                ),
                name="Clustered points",
                show=DataSourcesState.show_custom,
                clustering=C.EntityCluster.new(
                    enabled=DataSourcesState.clustering, pixel_range=40, minimum_cluster_size=3
                ),
            ),
            rs.cesium_events(viewer_id="data"),
            animation=True,
            timeline=True,
            should_animate=True,
        ),
    )
