"""Builders for canonical tower configuration components."""

from transmissionlines.models import TowerConfiguration


def build_tower_configuration(configuration: TowerConfiguration) -> TowerConfiguration:
    """Return the supplied canonical configuration unchanged."""
    return configuration


__all__ = ["build_tower_configuration"]
