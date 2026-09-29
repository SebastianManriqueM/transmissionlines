"""Select the installed cross-section shared by electrical and curve calculations."""

from transmissionlines.models.assets import CrossSectionTransmissionLine, RoutedTransmissionLine
from transmissionlines.models.configurations import TowerConfiguration
from transmissionlines.models.routing import ElectricalTower


def resolve_configuration(
    line: CrossSectionTransmissionLine | RoutedTransmissionLine, *, tower: ElectricalTower | None = None
) -> TowerConfiguration:
    """Select a line-owned tower cross-section or its unambiguous common one.

    Parameters
    ----------
    line : CrossSectionTransmissionLine or RoutedTransmissionLine
        Static input line whose cross-section is needed.
    tower : ElectricalTower, optional
        Explicit support on a routed line with varying configurations.

    Returns
    -------
    TowerConfiguration
        Registered configuration for the selected cross-section.

    Raises
    ------
    ValueError
        If selection is unnecessary, foreign, or ambiguous.
    """
    if isinstance(line, CrossSectionTransmissionLine):
        if tower is not None:
            raise ValueError("cross-section line does not accept a tower selection")
        return line.configuration
    towers = [line.spans[0].start_end.start, *(span.start_end.end for span in line.spans)]
    if tower is not None:
        for owned in towers:
            if owned.uuid == tower.uuid:
                return owned.configuration
        raise ValueError("selected tower does not belong to this line")
    configurations = {item.configuration.uuid for item in towers}
    if len(configurations) != 1:
        raise ValueError("routed line has different configurations; select a tower")
    return towers[0].configuration