"""Configuration builder surface."""
from transmissionlines.models.configurations import TowerConfiguration

def build_tower_configuration(configuration: TowerConfiguration) -> TowerConfiguration:
    """Return a validated configuration without mutating a system."""
    return configuration

__all__ = ["build_tower_configuration"]
