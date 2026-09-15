"""The Python -> JavaScript bridge to the Cesium API."""

from __future__ import annotations

import reflex as rx

import reflex_resium as rs
from reflex_resium.base import _is_memoizable


class GlobeState(rx.State):
    lon: float = 10.0


def test_namespace_access_imports_aliased_export():
    expr = rs.Cesium.Color.RED
    assert str(expr) == "Cesium_Color.RED"
    imports = dict(expr._get_all_var_data().imports)
    (import_var,) = imports["cesium"]
    assert import_var.tag == "Color"
    assert import_var.alias == "Cesium_Color"
    assert import_var.install is False


def test_cartesian3_builds_from_degrees_call():
    assert str(rs.cartesian3(1, 2, 3)) == "(Cesium_Cartesian3.fromDegrees(1, 2, 3))"


def test_color_with_alpha():
    assert str(rs.color("#f00", 0.5)) == '((Cesium_Color.fromCssColorString("#f00")).withAlpha(0.5))'


def test_new_with_kwargs_camel_cases_options():
    expr = rs.Cesium.OpenStreetMapImageryProvider.new(url="x", max_zoom=3)
    assert str(expr).startswith("(new Cesium_OpenStreetMapImageryProvider(")
    assert '["maxZoom"] : 3' in str(expr)


def test_cartesian3_array_flattens_pairs():
    assert str(rs.cartesian3_array([[1, 2], [3, 4]])) == "(Cesium_Cartesian3.fromDegreesArray([1, 2, 3, 4]))"


def test_state_vars_are_tracked_as_dependencies():
    expr = rs.cartesian3(GlobeState.lon, 2)
    assert len(expr._resium_deps) == 1
    assert _is_memoizable(expr)


def test_raw_js_without_deps_is_volatile():
    assert rs.js("1 + 1")._resium_volatile
    assert not _is_memoizable(rs.js("1 + 1"))
    assert not rs.js("1 + 1", deps=[])._resium_volatile


def test_memo_emits_use_memo_hook():
    memo = rs.osm_imagery_layer()
    name = str(memo)
    assert name.startswith("resium_memo_")
    (hook,) = memo._get_all_var_data().hooks
    assert hook.startswith("const " + name + " = useMemo(() => (new Cesium_ImageryLayer(")
    assert hook.endswith("[]);")


def test_memo_name_is_deterministic():
    assert str(rs.cartesian3(1, 2).memo()) == str(rs.cartesian3(1, 2).memo())
    assert str(rs.cartesian3(1, 2).memo()) != str(rs.cartesian3(2, 1).memo())


def test_component_props_are_memoized():
    rendered = str(rs.viewer(rs.entity(name="a", position=rs.cartesian3(1, 2, 3)), full=True))
    assert "jsx(Viewer" in rendered
    assert "position:resium_memo_" in rendered
