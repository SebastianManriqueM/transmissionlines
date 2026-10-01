"""Calculate and plot cross-section sag for the v2 3L11 Cardinal selection."""

from catalog_line import build_line

from transmissionlines.user_api import build, plots


def main() -> None:
    """Run the catalog-backed single-conductor sag example."""
    line = build_line()
    line.everyday_tension_fraction = 0.20
    results = build.calculations(
        line, impedances=False, st_clair=False,
        sag_options={
            "elastic_modulus_psi": 11.5e6,
            "thermal_expansion_per_k": 19.3e-6,
            "reference_temperature_c": 25,
            "operating_temperature_c": 75,
            "span_start_ft": 20, "span_stop_ft": 2000, "span_step_ft": 10,
        },
    )
    result = results.sag
    axes = plots.sag(result)
    assert len(axes.lines) == len(result.curves)
    print(len(result.curves))
    print(len(result.curves[0].span_lengths_ft))


if __name__ == "__main__":
    main()