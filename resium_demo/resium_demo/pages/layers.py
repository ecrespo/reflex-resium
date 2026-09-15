"""Imagery layers, glTF models and 3D Tiles / terrain."""

from __future__ import annotations

from typing import Any

import reflex as rx

import reflex_resium as rs

from ..common import DemoState, base_map_select, demo_viewer, labeled_slider, labeled_switch, page_shell, section

C = rs.Cesium

MODELS_BASE = "https://raw.githubusercontent.com/CesiumGS/cesium/main/Apps/SampleData/models"
SAMPLE_TILESET = (
    "https://raw.githubusercontent.com/CesiumGS/3d-tiles-samples/main/1.0/TilesetWithDiscreteLOD/tileset.json"
)
AIRPLANE = (-123.0744619, 44.0503706, 800)
TRUCK = (-123.0725, 44.0503706, 0)


class LayersState(DemoState):
    overlay: bool = True
    overlay_alpha: float = 0.8
    brightness: float = 1.0
    contrast: float = 1.0
    hue: float = 0.0
    saturation: float = 1.0
    gamma: float = 1.0
    split: bool = False
    models: bool = True
    model_scale: float = 1.0
    silhouette: bool = True
    tileset: bool = False
    tileset_info: dict = {}
    osm_buildings: bool = False
    world_terrain: bool = False

    @rx.event
    def set_field(self, field: str, value: Any):
        setattr(self, field, value)

    @rx.event
    def layer_event(self, layer: dict, index: float):
        self._push(f"ImageryLayerCollection event: index={index} {layer}")

    @rx.event
    def model_ready(self, info: dict):
        self._push(f"Model.on_ready {info}")

    @rx.event
    def model_error(self, message: str):
        self._push(f"Model.on_error {message}")

    @rx.event
    def tileset_ready(self, info: dict):
        self.tileset_info = info.get("bounding_sphere") or {}
        self._push(f"Cesium3DTileset.on_ready {self.tileset_info}")

    @rx.event
    def tileset_error(self, message: str):
        self._push(f"Cesium3DTileset.on_error {message}")

    @rx.event
    def feature_clicked(self, movement: dict, target: dict):
        self._push(f"3D Tiles feature {target}")


def s(field: str):
    return lambda value: LayersState.set_field(field, value)


def controls() -> rx.Component:
    return rx.vstack(
        base_map_select(),
        section(
            "Overlay ImageryLayer (labels)",
            labeled_switch("Show overlay", LayersState.overlay, s("overlay")),
            labeled_slider("alpha", LayersState.overlay_alpha, s("overlay_alpha"), 0, 1, 0.05),
        ),
        section(
            "Base layer adjustments",
            labeled_slider("brightness", LayersState.brightness, s("brightness"), 0, 3, 0.05),
            labeled_slider("contrast", LayersState.contrast, s("contrast"), 0, 3, 0.05),
            labeled_slider("hue", LayersState.hue, s("hue"), -3.14, 3.14, 0.05),
            labeled_slider("saturation", LayersState.saturation, s("saturation"), 0, 3, 0.05),
            labeled_slider("gamma", LayersState.gamma, s("gamma"), 0.1, 3, 0.05),
            labeled_switch("Split screen (Natural Earth on the left)", LayersState.split, s("split")),
        ),
        section(
            "glTF models (internet)",
            labeled_switch("Model + ModelGraphics", LayersState.models, s("models")),
            labeled_slider("Scale", LayersState.model_scale, s("model_scale"), 0.5, 5, 0.1),
            labeled_switch("Silhouette", LayersState.silhouette, s("silhouette")),
            rx.button(
                "Fly to models",
                size="1",
                on_click=rs.fly_to("layers", TRUCK[0], TRUCK[1] - 0.004, 250, pitch=-20, duration=3),
            ),
        ),
        section(
            "3D Tiles & terrain",
            labeled_switch("Public 3D Tiles sample", LayersState.tileset, s("tileset")),
            rx.cond(
                LayersState.tileset_info.contains("latitude"),
                rx.button(
                    "Fly to tileset",
                    size="1",
                    on_click=rs.fly_to(
                        "layers",
                        LayersState.tileset_info["longitude"],
                        LayersState.tileset_info["latitude"],
                        600,
                        pitch=-45,
                        duration=2,
                    ),
                ),
            ),
            labeled_switch("Cesium OSM Buildings (ion)", LayersState.osm_buildings, s("osm_buildings")),
            labeled_switch("Cesium World Terrain (ion)", LayersState.world_terrain, s("world_terrain")),
            rx.callout(
                "Cesium ion assets use Cesium's evaluation token unless you set CESIUM_ION_ACCESS_TOKEN "
                "(or ResiumPlugin(ion_access_token=...)). Switching terrain re-creates the Viewer.",
                icon="info",
                size="1",
            ),
            rx.button(
                "Fly to New York",
                size="1",
                variant="outline",
                on_click=rs.fly_to("layers", -74.019, 40.69, 900, heading=30, pitch=-25, duration=3),
            ),
        ),
        width="100%",
    )


def layers_page() -> rx.Component:
    airplane = rs.cartesian3(*AIRPLANE)
    return page_shell(
        "Imagery, models & 3D Tiles",
        "Stack and tune ImageryLayers, load glTF models as primitives or entity graphics, "
        "and stream 3D Tiles and terrain.",
        controls(),
        rx.cond(
            LayersState.world_terrain,
            demo_viewer(layers_children(airplane), terrain_provider=rs.world_terrain()),
            demo_viewer(layers_children(airplane)),
        ),
    )


def layers_children(airplane) -> rx.Component:
    return rx.fragment(
        rs.camera_fly_to(destination=rs.cartesian3(-100, 40, 9_000_000), duration=0, once=True),
        rs.imagery_layer_collection(
            on_layer_add=LayersState.layer_event,
            on_layer_remove=LayersState.layer_event,
            on_layer_show_or_hide=LayersState.layer_event,
        ),
        # Adjust the base layer (index 0) through a second layer tuned with state.
        rs.imagery_layer(
            imagery_provider=C.TileMapServiceImageryProvider.fromUrl(
                C.buildModuleUrl("Assets/Textures/NaturalEarthII")
            ),
            brightness=LayersState.brightness,
            contrast=LayersState.contrast,
            hue=LayersState.hue,
            saturation=LayersState.saturation,
            gamma=LayersState.gamma,
            split_direction=rx.cond(LayersState.split, C.SplitDirection.LEFT, C.SplitDirection.NONE),
            alpha=rx.cond(LayersState.split, 1.0, 0.0),
        ),
        rs.scene(split_position=0.5),
        rs.imagery_layer(
            imagery_provider=C.UrlTemplateImageryProvider.new(
                url="https://basemaps.cartocdn.com/rastertiles/voyager_only_labels/{z}/{x}/{y}.png",
                credit="© OpenStreetMap contributors © CARTO",
            ),
            show=LayersState.overlay,
            alpha=LayersState.overlay_alpha,
        ),
        rx.cond(
            LayersState.models,
            rx.fragment(
                rs.model(
                    url=f"{MODELS_BASE}/CesiumAir/Cesium_Air.glb",
                    model_matrix=C.Transforms.eastNorthUpToFixedFrame(airplane),
                    minimum_pixel_size=64,
                    scale=LayersState.model_scale,
                    silhouette_color=C.Color.CYAN,
                    silhouette_size=rx.cond(LayersState.silhouette, 2.0, 0.0),
                    on_ready=LayersState.model_ready,
                    on_error=LayersState.model_error,
                ),
                rs.entity(
                    rs.model_graphics(
                        uri=f"{MODELS_BASE}/CesiumMilkTruck/CesiumMilkTruck.glb",
                        minimum_pixel_size=48,
                        scale=LayersState.model_scale,
                        silhouette_color=C.Color.ORANGE,
                        silhouette_size=rx.cond(LayersState.silhouette, 2.0, 0.0),
                        run_animations=True,
                    ),
                    name="Milk truck (ModelGraphics)",
                    position=rs.cartesian3(*TRUCK),
                    orientation=C.Transforms.headingPitchRollQuaternion(
                        rs.cartesian3(*TRUCK), rs.heading_pitch_roll(135, 0, 0)
                    ),
                ),
            ),
        ),
        rx.cond(
            LayersState.tileset,
            rs.cesium_3d_tileset(
                url=SAMPLE_TILESET,
                on_ready=LayersState.tileset_ready,
                on_error=LayersState.tileset_error,
                on_click=LayersState.feature_clicked,
            ),
        ),
        rx.cond(
            LayersState.osm_buildings,
            rs.cesium_3d_tileset(
                url=rs.ion_resource(96188),
                cesium_style=C.Cesium3DTileStyle.new({"color": "color('#e2e8f0')"}),
                on_ready=LayersState.tileset_ready,
                on_error=LayersState.tileset_error,
                on_click=LayersState.feature_clicked,
            ),
        ),
        rs.cesium_events(viewer_id="layers"),
    )
