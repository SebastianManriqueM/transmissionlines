"""Calculate and plot cross-section sag for the v2 3L11 Cardinal selection."""

from catalog_line import build_line

from transmissionlines.api import calculate_sag, plot_sag_curve
from transmissionlines.models import SagOptions
from transmissionlines.units import ElasticModulus, ThermalExpansion


def main() -> None:
    """Run the catalog-backed single-conductor sag example."""
    line = build_line()
    line.everyday_tension_fraction = 0.20
    options = SagOptions(
        elastic_modulus=ElasticModulus(11.5e6, "psi"),
        thermal_expansion_coefficient=ThermalExpansion(19.3e-6, "1 / kelvin"),
    )
    result = calculate_sag(line, options=options)
    axes = plot_sag_curve(result)
    assert len(axes.lines) == len(result.curves)
    print(len(result.curves))
    print(len(result.curves[0].span_lengths_ft))


if __name__ == "__main__":
    main()