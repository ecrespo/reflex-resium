"""reflex-resium demo: a tour of resium (React components for Cesium) in Reflex."""

import reflex as rx

from .pages.camera import camera_page
from .pages.data_sources import data_sources_page
from .pages.graphics import graphics_page
from .pages.home import entities_page
from .pages.layers import layers_page
from .pages.primitives import primitives_page
from .pages.scene import scene_page
from .pages.widget import widget_page

app = rx.App()

app.add_page(entities_page, route="/", title="Entities & state · reflex-resium")
app.add_page(graphics_page, route="/graphics", title="Entity graphics · reflex-resium")
app.add_page(primitives_page, route="/primitives", title="Primitives · reflex-resium")
app.add_page(data_sources_page, route="/data-sources", title="Data sources · reflex-resium")
app.add_page(camera_page, route="/camera", title="Camera & events · reflex-resium")
app.add_page(scene_page, route="/scene", title="Scene & effects · reflex-resium")
app.add_page(layers_page, route="/layers", title="Imagery, models & 3D Tiles · reflex-resium")
app.add_page(widget_page, route="/widget", title="CesiumWidget · reflex-resium")
