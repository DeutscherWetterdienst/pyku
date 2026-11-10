import pytest

from pyku.visualisation import (
    _parse_map_layout,
    _resolve_subplot_layout,
)


@pytest.mark.parametrize(
    ("layout", "n_plots", "expected"),
    [
        ("3x3", 7, (3, 3)),
        ("x3", 7, (3, 3)),
        ("4x", 10, (4, 3)),
        (" 2 X 4 ", 5, (2, 4)),
    ],
)
def test_parse_map_layout(
    layout: str,
    n_plots: int,
    expected: tuple[int, int],
) -> None:
    assert _parse_map_layout(layout, n_plots) == expected


@pytest.mark.parametrize("layout", ["", "x", "3", "0x2", "2x0"])
def test_parse_map_layout_rejects_invalid_values(
    layout: str,
) -> None:
    with pytest.raises(ValueError, match="layout"):
        _parse_map_layout(layout, 4)


def test_resolve_subplot_layout_warns_about_extra_slots(
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert _resolve_subplot_layout("3x3", 4, "seasonal") == (3, 3)
    assert "provides 9 subplot slots for 4 seasonal plots" in caplog.text


def test_resolve_subplot_layout_warns_before_rejecting_too_few_slots(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with pytest.raises(ValueError, match="provides 3 subplot slots"):
        _resolve_subplot_layout("1x3", 4, "seasonal")
    assert "provides 3 subplot slots for 4 seasonal plots" in caplog.text
