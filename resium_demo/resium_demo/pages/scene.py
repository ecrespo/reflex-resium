"""Scene, Globe, atmosphere, Sun/Moon, Fog, Clock, ShadowMap, post-processing, particles."""

from __future__ import annotations

from typing import Any

import reflex as rx

import reflex_resium as rs

from ..common import DemoState, base_map_select, demo_viewer, labeled_slider, labeled_switch, page_shell, section

C = rs.Cesium

SPARK_SVG = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='32' height='32'><defs><radialGradient id='g'>"
    "<stop offset='0' stop-color='white'/><stop offset='0.35' stop-color='%23ffd27a'/>"
    "<stop offset='1' stop-color='%23ff5a00' stop-opacity='0'/></radialGradient></defs>"
    "<circle cx='16' cy='16' r='16' fill='url(%23g)'/></svg>"
)

FIRE = (-16.642, 28.272)


class SceneState(DemoState):
    hour: float = 18
    multiplier: float = 600
    animate: bool = False
    lighting: bool = True
    ground_atmosphere: bool = True
    sky_atmosphere: bool = True
    hue_shift: float = 0
    fog: bool = True
    fog_density: float = 0.0006
    sun: bool = True
    moon: bool = True
    fps: bool = False
    shadows: bool = True
    black_and_white: bool = False
    gradations: float = 5
    brightness_stage: bool = False
    brightness: float = 1.5
    night_vision: bool = False
    bloom: bool = False
    bloom_contrast: float = 128
    lens_flare: bool = False
    fxaa: bool = True
    particles: bool = True
    emission_rate: float = 60
    ticks: int = 0

    @rx.var
    def current_time(self) -> str:
        h = int(self.hour)
        m = int((self.hour - h) * 60)
        return f"2026-06-21T{h:02d}:{m:02d}:00Z"

    @rx.event
    def set_field(self, field: str, value: Any):
        setattr(self, field, value)

    @rx.event
    def on_tick(self, clock: dict):
        self.ticks += 1

    @rx.event
    def go_to_fire(self):
        # Particles advance with the scene clock: animate it in real time.
        self.animate = True
        self.multiplier = 1
        self._push("clock animating at 1x for the ParticleSystem")
        return rs.fly_to("scene", FIRE[0], FIRE[1] - 0.0045, 350, pitch=-20, duration=3)

    @rx.event
    def on_morph(self):
        self._push("Scene.on_morph_complete")


def s(field: str):
    """Setter shortcut for a SceneState field."""
    return lambda value: SceneState.set_field(field, value)


def controls() -> rx.Component:
    return rx.vstack(
        base_map_select(),
        section(
            "Clock",
            labeled_slider("Time of day (UTC h)", SceneState.hour, s("hour"), 0, 23.75, 0.25),
            rx.text("current_time: ", rx.code(SceneState.current_time), size="1"),
            labeled_switch("Animate (should_animate)", SceneState.animate, s("animate")),
            labeled_slider("Multiplier", SceneState.multiplier, s("multiplier"), 1, 3600, 1),
            rx.text("Clock.on_tick events (throttled 1/s): ", rx.code(SceneState.ticks.to_string()), size="1"),
        ),
        section(
            "Globe & sky",
            labeled_switch("Globe.enable_lighting", SceneState.lighting, s("lighting")),
            labeled_switch("Globe.show_ground_atmosphere", SceneState.ground_atmosphere, s("ground_atmosphere")),
            labeled_switch("SkyAtmosphere", SceneState.sky_atmosphere, s("sky_atmosphere")),
            labeled_slider("SkyAtmosphere hue shift", SceneState.hue_shift, s("hue_shift"), -1, 1, 0.05),
            labeled_switch("Fog", SceneState.fog, s("fog")),
            labeled_slider("Fog density", SceneState.fog_density, s("fog_density"), 0, 0.003, 0.0001),
            labeled_switch("Sun", SceneState.sun, s("sun")),
            labeled_switch("Moon", SceneState.moon, s("moon")),
            labeled_switch("ShadowMap", SceneState.shadows, s("shadows")),
            labeled_switch("Scene FPS counter", SceneState.fps, s("fps")),
        ),
        section(
            "Post-processing stages",
            labeled_switch("Fxaa", SceneState.fxaa, s("fxaa")),
            labeled_switch("BlackAndWhiteStage", SceneState.black_and_white, s("black_and_white")),
            labeled_slider("Gradations", SceneState.gradations, s("gradations"), 1, 20),
            labeled_switch("BrightnessStage", SceneState.brightness_stage, s("brightness_stage")),
            labeled_slider("Brightness", SceneState.brightness, s("brightness"), 0, 3, 0.1),
            labeled_switch("NightVisionStage", SceneState.night_vision, s("night_vision")),
            labeled_switch("Bloom", SceneState.bloom, s("bloom")),
            labeled_slider("Bloom contrast", SceneState.bloom_contrast, s("bloom_contrast"), -255, 255, 1),
            labeled_switch("LensFlareStage", SceneState.lens_flare, s("lens_flare")),
        ),
        section(
            "ParticleSystem",
            labeled_switch("Fire on Teide", SceneState.particles, s("particles")),
            labeled_slider("Emission rate", SceneState.emission_rate, s("emission_rate"), 5, 300, 5),
            rx.text(
                "Particles need an animating clock; the button below enables it at 1x.", size="1", color_scheme="gray"
            ),
            rx.button("Fly to the fire", size="1", on_click=SceneState.go_to_fire),
            rx.button(
                "Sunset from space",
                size="1",
                variant="outline",
                on_click=rs.fly_to("scene", -20, 20, 15_000_000, duration=2),
            ),
        ),
        width="100%",
    )


def scene_page() -> rx.Component:
    fire_position = rs.cartesian3(FIRE[0], FIRE[1], 0)
    return page_shell(
        "Scene & effects",
        "Scene-level components configure the renderer declaratively: lighting follows "
        "the Clock, stages toggle on and off, and a ParticleSystem burns on Teide.",
        controls(),
        demo_viewer(
            rs.camera_fly_to(destination=rs.cartesian3(-20, 20, 15_000_000), duration=0, once=True),
            rs.scene(debug_show_frames_per_second=SceneState.fps, on_morph_complete=SceneState.on_morph),
            rs.globe(
                enable_lighting=SceneState.lighting,
                show_ground_atmosphere=SceneState.ground_atmosphere,
                dynamic_atmosphere_lighting=True,
            ),
            rs.sky_atmosphere(show=SceneState.sky_atmosphere, hue_shift=SceneState.hue_shift),
            rs.fog(enabled=SceneState.fog, density=SceneState.fog_density),
            rs.sun(show=SceneState.sun, glow_factor=1.5),
            rs.moon(show=SceneState.moon),
            rs.clock(
                current_time=rs.julian_date(SceneState.current_time),
                multiplier=SceneState.multiplier,
                should_animate=SceneState.animate,
                on_tick=SceneState.on_tick.throttle(1000),
            ),
            rs.shadow_map(enabled=SceneState.shadows, soft_shadows=True, darkness=0.4),
            rs.fxaa(enabled=SceneState.fxaa),
            rs.black_and_white_stage(enabled=SceneState.black_and_white, gradations=SceneState.gradations),
            rs.brightness_stage(enabled=SceneState.brightness_stage, brightness=SceneState.brightness),
            rs.night_vision_stage(enabled=SceneState.night_vision),
            rs.bloom(enabled=SceneState.bloom, contrast=SceneState.bloom_contrast, brightness=-0.2, glow_only=False),
            rs.lens_flare_stage(enabled=SceneState.lens_flare, intensity=5, distortion=10),
            rs.entity(
                rs.box_graphics(
                    dimensions=C.Cartesian3.new(30, 30, 120),
                    material=rs.color("#e2e8f0"),
                    shadows=C.ShadowMode.ENABLED,
                ),
                name="Shadow caster",
                position=rs.cartesian3(FIRE[0] + 0.0006, FIRE[1] + 0.0004, 60),
            ),
            rx.cond(
                SceneState.particles,
                rs.particle_system(
                    image=SPARK_SVG,
                    model_matrix=C.Transforms.eastNorthUpToFixedFrame(fire_position),
                    emitter=C.ConeEmitter.new(C.Math.toRadians(25)),
                    emission_rate=SceneState.emission_rate,
                    image_size=rs.cartesian2(22, 22),
                    start_scale=1.0,
                    end_scale=4.0,
                    minimum_particle_life=1.0,
                    maximum_particle_life=2.2,
                    minimum_speed=8.0,
                    maximum_speed=18.0,
                    start_color=C.Color.fromCssColorString("#ffd27a").withAlpha(0.9),
                    end_color=C.Color.fromCssColorString("#ff3d00").withAlpha(0.0),
                ),
            ),
            rs.cesium_events(viewer_id="scene"),
            animation=True,
            timeline=True,
        ),
    )
