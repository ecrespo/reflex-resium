"""Camera components, camera controller, screen-space events and imperative helpers."""

from __future__ import annotations

import reflex as rx

import reflex_resium as rs

from ..common import DemoState, base_map_select, demo_viewer, labeled_slider, labeled_switch, page_shell, section

C = rs.Cesium

DESTINATIONS = {
    "caracas": ("Caracas & El Ávila", -66.87, 10.40, 25_000, 0, -35),
    "barcelona": ("Barcelona", 2.17, 41.30, 18_000, 10, -40),
    "everest": ("Himalaya", 86.92, 27.60, 90_000, 0, -30),
    "grand_canyon": ("Grand Canyon", -112.11, 35.95, 40_000, 20, -35),
    "tokyo": ("Tokyo Bay", 139.78, 35.45, 60_000, 0, -45),
}


class CameraState(DemoState):
    destination: str = "caracas"
    duration: float = 3
    heading_offset: float = 0
    look_at: bool = False
    orbit_range: float = 30_000
    enable_rotate: bool = True
    enable_zoom: bool = True
    enable_tilt: bool = True
    camera_info: dict = {}
    cursor: dict = {}
    screenshot_url: str = ""
    moves: int = 0

    @rx.var
    def dest_lon(self) -> float:
        return DESTINATIONS[self.destination][1]

    @rx.var
    def dest_lat(self) -> float:
        return DESTINATIONS[self.destination][2]

    @rx.var
    def dest_height(self) -> float:
        return DESTINATIONS[self.destination][3]

    @rx.var
    def dest_heading(self) -> float:
        return DESTINATIONS[self.destination][4] + self.heading_offset

    @rx.var
    def dest_pitch(self) -> float:
        return DESTINATIONS[self.destination][5]

    @rx.event
    def set_destination(self, value: str):
        self.destination = value
        self.look_at = False
        self._push(f"CameraFlyTo → {DESTINATIONS[value][0]}")

    @rx.event
    def set_duration(self, value: float):
        self.duration = value

    @rx.event
    def set_heading_offset(self, value: float):
        self.heading_offset = value

    @rx.event
    def set_look_at(self, value: bool):
        self.look_at = value

    @rx.event
    def set_orbit_range(self, value: float):
        self.orbit_range = value

    @rx.event
    def set_enable_rotate(self, value: bool):
        self.enable_rotate = value

    @rx.event
    def set_enable_zoom(self, value: bool):
        self.enable_zoom = value

    @rx.event
    def set_enable_tilt(self, value: bool):
        self.enable_tilt = value

    @rx.event
    def on_camera_change(self, info: dict):
        self.camera_info = {k: round(v, 4) for k, v in info.items() if isinstance(v, (int, float))}

    @rx.event
    def on_move_end(self):
        self.moves += 1

    @rx.event
    def on_fly_complete(self):
        self._push("CameraFlyTo.on_complete")

    @rx.event
    def on_mouse_move(self, info: dict):
        self.cursor = info

    @rx.event
    def on_double_click(self, movement: dict):
        self._push(f"ScreenSpaceEvent LEFT_DOUBLE_CLICK at {movement.get('position')}")

    @rx.event
    def on_camera_read(self, info: dict):
        self._push(f"get_camera → {info}")

    @rx.event
    def on_screenshot(self, data_url: str):
        self.screenshot_url = data_url or ""
        self._push("screenshot captured")

    @rx.event
    def on_wheel(self, delta: float):
        self._push(f"Viewer.on_wheel delta={delta}")


def controls() -> rx.Component:
    return rx.vstack(
        base_map_select(),
        section(
            "CameraFlyTo (declarative)",
            rx.select.root(
                rx.select.trigger(width="100%"),
                rx.select.content(*[rx.select.item(v[0], value=k) for k, v in DESTINATIONS.items()]),
                value=CameraState.destination,
                on_change=CameraState.set_destination,
            ),
            labeled_slider("Duration (s)", CameraState.duration, CameraState.set_duration, 0, 10, 0.5),
            labeled_slider(
                "Heading offset (°)", CameraState.heading_offset, CameraState.set_heading_offset, -180, 180, 5
            ),
        ),
        section(
            "CameraLookAt (orbit lock)",
            labeled_switch("Lock camera on destination", CameraState.look_at, CameraState.set_look_at),
            labeled_slider("Range (m)", CameraState.orbit_range, CameraState.set_orbit_range, 2_000, 200_000, 1_000),
        ),
        section(
            "ScreenSpaceCameraController",
            labeled_switch("Rotate", CameraState.enable_rotate, CameraState.set_enable_rotate),
            labeled_switch("Zoom", CameraState.enable_zoom, CameraState.set_enable_zoom),
            labeled_switch("Tilt", CameraState.enable_tilt, CameraState.set_enable_tilt),
        ),
        section(
            "Imperative helpers (rx.call_function)",
            rx.hstack(
                rx.button("3D", size="1", on_click=rs.morph_to("camera", "3D")),
                rx.button("2D", size="1", on_click=rs.morph_to("camera", "2D")),
                rx.button("Columbus", size="1", on_click=rs.morph_to("camera", "COLUMBUS_VIEW")),
                rx.button("Home", size="1", variant="outline", on_click=rs.fly_home("camera", 2)),
                wrap="wrap",
            ),
            rx.hstack(
                rx.button(
                    "set_view Madrid",
                    size="1",
                    variant="soft",
                    on_click=rs.set_view("camera", -3.70, 40.30, 30_000, pitch=-45),
                ),
                rx.button(
                    "get_camera", size="1", variant="soft", on_click=rs.get_camera("camera", CameraState.on_camera_read)
                ),
                rx.button(
                    "Screenshot", size="1", variant="soft", on_click=rs.screenshot("camera", CameraState.on_screenshot)
                ),
                wrap="wrap",
            ),
            rx.cond(
                CameraState.screenshot_url != "",
                rx.image(src=CameraState.screenshot_url, width="100%", border_radius="6px"),
            ),
        ),
        section(
            "Live camera (CesiumEvents.on_camera_change)",
            rx.foreach(
                CameraState.camera_info,
                lambda kv: rx.hstack(
                    rx.text(kv[0], size="1"), rx.spacer(), rx.code(kv[1].to_string(), size="1"), width="100%"
                ),
            ),
            rx.text("Camera.on_move_end count: ", rx.code(CameraState.moves.to_string()), size="2"),
            rx.text(
                "Cursor: ",
                rx.code(CameraState.cursor["latitude"].to_string()),
                " ",
                rx.code(CameraState.cursor["longitude"].to_string()),
                size="2",
            ),
            rx.text("Double-click the globe to fire a ScreenSpaceEvent.", size="2", color_scheme="gray"),
        ),
        width="100%",
    )


def camera_page() -> rx.Component:
    lon, lat, height = CameraState.dest_lon, CameraState.dest_lat, CameraState.dest_height
    return page_shell(
        "Camera & events",
        "Declarative camera flights and locks, input controller settings, raw screen-space "
        "events and imperative helpers that call the Cesium camera from event handlers.",
        controls(),
        demo_viewer(
            rx.cond(
                CameraState.look_at,
                rs.camera_look_at(
                    target=rs.cartesian3(lon, lat, 0),
                    offset=rs.heading_pitch_range(CameraState.heading_offset, -35, CameraState.orbit_range),
                ),
                rs.camera_fly_to(
                    destination=rs.cartesian3(lon, lat, height),
                    orientation=rs.camera_orientation(CameraState.dest_heading, CameraState.dest_pitch),
                    duration=CameraState.duration,
                    on_complete=CameraState.on_fly_complete,
                ),
            ),
            rs.camera(on_move_end=CameraState.on_move_end, percentage_changed=0.05),
            rs.screen_space_camera_controller(
                enable_rotate=CameraState.enable_rotate,
                enable_zoom=CameraState.enable_zoom,
                enable_tilt=CameraState.enable_tilt,
            ),
            rs.screen_space_event_handler(
                rs.screen_space_event(
                    action=CameraState.on_double_click, type=C.ScreenSpaceEventType.LEFT_DOUBLE_CLICK
                ),
            ),
            rs.cesium_events(
                viewer_id="camera",
                on_camera_change=CameraState.on_camera_change,
                on_ready=CameraState.on_camera_change,
                on_mouse_move=CameraState.on_mouse_move,
                mouse_move_throttle=200,
            ),
            on_wheel=CameraState.on_wheel.throttle(1000),
        ),
    )
