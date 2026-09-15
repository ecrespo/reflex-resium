# reflex-resium

[![Quality](https://github.com/ecrespo/reflex-resium/actions/workflows/quality.yml/badge.svg)](https://github.com/ecrespo/reflex-resium/actions/workflows/quality.yml)
[![Security](https://github.com/ecrespo/reflex-resium/actions/workflows/security.yml/badge.svg)](https://github.com/ecrespo/reflex-resium/actions/workflows/security.yml)
[![PyPI](https://img.shields.io/pypi/v/reflex-resium)](https://pypi.org/project/reflex-resium/)

[Resium](https://resium.reearth.io) (React components for 🌏 [Cesium](https://cesium.com)) wrapped for [Reflex](https://reflex.dev): build 3D globes and maps — entities, primitives, GeoJSON/KML/CZML, 3D Tiles, terrain, camera flights, post-processing — in pure Python.

- **All 97 resium components** (resium 1.26.0 / cesium 1.145.0), generated from resium's TypeScript definitions with prop docs and types.
- **`rs.Cesium` bridge**: build real Cesium objects (`Cartesian3`, `Color`, imagery providers, materials, enums…) from Python, including state vars and `rx.foreach` items.
- **Automatic memoization** of Cesium objects so read-only props don't re-create elements on every render.
- **JSON-safe events**: Cesium callbacks (`on_click`, `on_load`, `on_tick`, `on_ready`…) arrive in your state as dictionaries.
- **`cesium_events`**: geographic clicks / mouse moves (longitude, latitude, height, picked entity), camera changes and selection.
- **Imperative helpers**: `fly_to`, `set_view`, `fly_home`, `zoom_to_entity`, `morph_to`, `set_clock`, `get_camera`, `screenshot`.
- **`ResiumPlugin`**: serves Cesium's static assets locally in dev and copies them into production builds (without it, the jsDelivr CDN is used).

## Installation

```bash
pip install reflex-resium     # or: uv add reflex-resium
```

## Quick start

```python
import reflex as rx
import reflex_resium as rs


def index() -> rx.Component:
    return rx.box(
        rs.viewer(
            rs.entity(
                rs.point_graphics(pixel_size=12, color=rs.Cesium.Color.RED),
                rs.entity_description(rx.heading("Tokyo"), rx.text("Hello from Reflex!")),
                name="Tokyo",
                position=rs.cartesian3(139.767052, 35.681167, 100),
            ),
            full=True,
        ),
        position="relative",
        height="100vh",
    )


app = rx.App()
app.add_page(index)
```

`rxconfig.py` (recommended):

```python
import reflex as rx
from reflex_resium import ResiumPlugin

config = rx.Config(
    app_name="my_app",
    plugins=[rx.plugins.RadixThemesPlugin(), ResiumPlugin()],
)
```

## Concepts

### Components

Every resium component is available as a class (`rs.Viewer`) and a snake_case factory (`rs.viewer`). Props are snake_case (`pixel_size` → `pixelSize`). Nest them exactly like in resium:

```python
rs.viewer(
    rs.custom_data_source(rs.entity(...), name="points"),
    rs.camera_fly_to(destination=rs.cartesian3(-66.9, 10.48, 50_000), duration=3),
    rs.globe(enable_lighting=True),
    rs.bloom(enabled=State.bloom),
    full=True,
)
```

Props named `style` that are Cesium values (`Cesium3DTileset`, `Label`, WMTS…) are exposed as `cesium_style`; root components (`viewer`, `cesium_widget`) keep Reflex's `style`, `id` and `class_name`.

### The `rs.Cesium` bridge

```python
C = rs.Cesium
C.Cartesian3.fromDegrees(State.lon, State.lat, 1000)
C.Color.fromCssColorString("#22d3ee").withAlpha(0.5)
C.HeightReference.CLAMP_TO_GROUND
C.OpenStreetMapImageryProvider.new(url="https://tile.openstreetmap.org/")  # new X({url})
C.Material.fromType("Checkerboard", {"repeat": rs.cartesian2(20, 10)})
rs.js("Array.from({length: 8}, (_, i) => i)")  # raw JS escape hatch
```

Keyword arguments become a camelCase options object. Helpers: `cartesian3`, `cartesian3_array`, `cartesian3_array_heights`, `cartesian2`, `color`, `rectangle_from_degrees`, `heading_pitch_roll`, `heading_pitch_range`, `camera_orientation`, `near_far_scalar`, `distance_display_condition`, `bounding_sphere`, `julian_date`, `time_interval_collection`, `ion_resource`, `natural_earth_imagery_layer`, `osm_imagery_layer`, `url_template_imagery_layer`, `ion_imagery_layer`, `world_terrain`, `ellipsoid_terrain`.

Cesium expressions passed as props are wrapped in `useMemo` (dependencies = the state vars they use). Use `.volatile()` to opt out or `.memo(*deps)` for explicit dependencies.

### Events

```python
class State(rx.State):
    @rx.event
    def clicked(self, movement: dict, target: dict):
        # movement = {"position": {"x", "y"}, ...}; target = {"id", "name", "kind", "properties"}
        ...


rs.entity(..., on_click=State.clicked)
rs.geo_json_data_source(data="/data.geojson", on_load=State.loaded)  # {"name", "entity_count", ...}
rs.clock(on_tick=State.tick.throttle(1000))  # throttle high-frequency events
```

### Geographic events and imperative camera control

```python
rs.viewer(
    ...,
    rs.cesium_events(
        viewer_id="main",
        on_left_click=State.on_click,  # {"longitude", "latitude", "height", "screen", "picked"}
        on_mouse_move=State.on_move,  # throttled (mouse_move_throttle=100 ms)
        on_camera_change=State.on_camera,  # {"longitude", "latitude", "height", "heading", "pitch", "roll"}
        on_selected_entity_change=State.on_select,
    ),
)

rx.button("Caracas", on_click=rs.fly_to("main", -66.9, 10.48, 20_000, pitch=-35, duration=3))
rx.button("Photo", on_click=rs.screenshot("main", State.save_png))
```

### Notes and gotchas

- **Camera operations** (`camera_fly_to`, `camera_look_at`, `camera_fly_home`, `camera_fly_to_bounding_sphere`) run in resium on every render. The wrappers memoize them (callbacks ignored in the comparison), so they only run again when a real prop changes.
- **`cesium_widget`** wraps its children with `CesiumWidgetContext`, exposing Cesium's `entities`/`dataSources`, which resium only provides for `viewer`.
- **`entity_description`** renders into Cesium's InfoBox iframe: Emotion/Radix classes don't apply there, so use `rx.el.*` with inline styles (`custom_attrs={"style": {...}}`).
- **ParticleSystem** advances with the scene clock: it needs `should_animate=True`.
- In development React `StrictMode` mounts components twice, so load events (`on_load`, `on_ready`) may fire twice; production builds fire once.

## Cesium assets and ion token

Cesium needs its `Workers`, `Assets`, `ThirdParty` and `Widgets` folders at runtime (`CESIUM_BASE_URL`):

| Setup | Assets served from |
| --- | --- |
| `ResiumPlugin()` | `node_modules/cesium/Build/Cesium` via a Vite middleware in dev; copied to `cesium/` in `reflex export` |
| `ResiumPlugin(base_url="https://my.cdn/cesium/")` | your URL |
| no plugin | `CESIUM_BASE_URL` env var, else jsDelivr CDN |

Cesium ion assets (world terrain, OSM Buildings, Bing imagery) need a token: `ResiumPlugin(ion_access_token="...")` or the `CESIUM_ION_ACCESS_TOKEN` environment variable. Without it Cesium's evaluation token is used and a banner is shown. `natural_earth_imagery_layer()` works offline with no token.

## Demo

```bash
cd resium_demo
uv pip install -e ..   # or pip install -e ..
reflex run
```

Pages: entities & state · entity graphics · primitives & clouds · data sources (GeoJSON, KML, CZML, clustering) · camera & events · scene & post-processing & particles · imagery, glTF models & 3D Tiles · CesiumWidget.

## Regenerating the wrappers

`custom_components/reflex_resium/components.py` is generated:

```bash
# in a scratch folder with resium, cesium, react and typescript@5 installed
node scripts/extract_props.mjs                 # -> props.json
python scripts/generate_components.py props.json path/to/resium/src
```

## Development

```bash
uv sync                                          # project + locked dev tools (uv.lock)
uv run ruff check . && uv run ruff format --check .  # lint + format
uv run pytest                                    # tests
```

CI runs on every push/PR to `develop` and `main`:

- **Quality** (`.github/workflows/quality.yml`): Ruff (version locked in `uv.lock`), pytest on Python 3.10–3.13, `uv build` + `twine check` + wheel smoke test, demo compilation.
- **Security** (`.github/workflows/security.yml`): Bandit, pip-audit, Gitleaks, dependency review and CodeQL (also weekly).

### Releasing

Bump `__version__` in `custom_components/reflex_resium/__init__.py`, merge to `main`, then tag it:

```bash
git tag v0.1.0 && git push origin v0.1.0
```

`.github/workflows/release.yml` checks that the tag matches the version, tests and builds the package, publishes it to PyPI through Trusted Publishing (environment `pypi`) and creates the GitHub Release with the distributions attached.

## License

MIT © Ernesto Crespo. Resium and Cesium are licensed under MIT and Apache-2.0 respectively.
