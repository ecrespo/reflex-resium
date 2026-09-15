"""Public API surface and imperative helpers."""

from __future__ import annotations

import importlib.metadata

import pytest
from reflex.event import EventSpec

import reflex_resium as rs


def test_version_matches_distribution_metadata():
    assert importlib.metadata.version("reflex-resium") == rs.__version__


def test_every_public_name_is_importable():
    missing = [name for name in rs.__all__ if not hasattr(rs, name)]
    assert missing == []


@pytest.mark.parametrize("factory", ["viewer", "cesium_widget", "entity", "camera_fly_to", "geo_json_data_source"])
def test_component_factories_are_exported(factory):
    assert callable(getattr(rs, factory))


@pytest.mark.parametrize(
    "spec",
    [
        rs.fly_to("globe", 1, 2),
        rs.set_view("globe", 1, 2),
        rs.fly_home("globe"),
        rs.zoom_to_entity("globe", "e1"),
        rs.morph_to("globe", "2d"),
        rs.set_clock("globe", multiplier=2),
    ],
)
def test_imperative_helpers_return_event_specs(spec):
    assert isinstance(spec, EventSpec)
    code = str(spec.args[0][1])
    assert "window.reflexResiumApi" in code
    assert '"globe"' in code


def test_morph_to_upper_cases_mode():
    assert '"2D"' in str(rs.morph_to("globe", "2d").args[0][1])
