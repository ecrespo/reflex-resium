import reflex as rx
from reflex.plugins.sitemap import SitemapPlugin

from reflex_resium import ResiumPlugin

config = rx.Config(
    app_name="resium_demo",
    plugins=[
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(appearance="dark", accent_color="cyan", radius="medium"),
        ),
        # Serves Cesium's Workers/Assets/Widgets locally (dev) and copies them into
        # the production build. Pass ion_access_token="..." or set the
        # CESIUM_ION_ACCESS_TOKEN environment variable to use Cesium ion assets.
        ResiumPlugin(),
    ],
    disable_plugins=[SitemapPlugin],
)
