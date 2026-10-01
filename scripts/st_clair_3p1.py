"""Calculate and export St. Clair, sequence impedances, and sag for tower 3P1.

Run from the repository root with::

    uv run python scripts/st_clair_3p1.py

The example uses Cardinal ACSR (54/7, 1.196 in), two subconductors per phase
at 18-inch spacing, and an Alumoweld 7/8 ground wire. The insulator, everyday
tension fraction, elastic modulus, and expansion coefficient are illustrative
study inputs rather than catalog recommendations. Cardinal's v2 GMR is an
outer-radius estimate and emits a warning; verify it before engineering use.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt

from transmissionlines.user_api import build, plots


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog-path",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "catalog" / "v2",
        help="normalized catalog directory (default: repository data/catalog/v2)",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("st_clair_3p1_curve.csv"),
        help="destination for the St. Clair curve samples",
    )
    parser.add_argument(
        "--output-figure",
        type=Path,
        default=Path("st_clair_3p1_curve.png"),
        help="destination for the St. Clair curve figure",
    )
    parser.add_argument("--output-sag-csv", type=Path, default=Path("st_clair_3p1_sag.csv"))
    parser.add_argument("--output-sag-figure", type=Path, default=Path("st_clair_3p1_sag.png"))
    parser.add_argument("--length-start-mi", type=float, default=20.0)
    parser.add_argument("--length-stop-mi", type=float, default=600.0)
    parser.add_argument("--length-step-mi", type=float, default=20.0)
    parser.add_argument("--span-start-ft", type=float, default=100.0)
    parser.add_argument("--span-stop-ft", type=float, default=200.0)
    parser.add_argument("--span-step-ft", type=float, default=50.0)
    return parser.parse_args()


def _print_sequence_impedances(electrical) -> None:
    matrix = electrical.matrices["Z012_ft"]
    print(f"\nFully transposed sequence impedance matrix Z012_ft ({matrix.unit})")
    print("row\\column\t" + "\t".join(matrix.column_labels))
    for label, real_row, imaginary_row in zip(
        matrix.row_labels, matrix.real, matrix.imaginary, strict=True
    ):
        values = [
            f"{real:.9f}{imaginary:+.9f}j"
            for real, imaginary in zip(real_row, imaginary_row, strict=True)
        ]
        print(f"{label}\t" + "\t".join(values))


def main() -> None:
    args = _parse_args()
    catalog = build.open_catalog(args.catalog_path)
    geometry = catalog.towers(structure_code="3P1")[0]
    geometry_id = geometry["record_id"]
    circuit_id = catalog.tower_circuits(geometry_id)[0]
    conductor = build.conductor(catalog, record_id="ACSR:954:cardinal:standard:54/7")
    ground_wire = build.ground_wire(catalog, record_id="Alumoweld:7/8:115.6:16")
    tower = build.tower(
        catalog, geometry_id=geometry_id, name="3P1-tower", ground_wire=ground_wire,
        circuits=[{
            "circuit_id": circuit_id, "conductor": conductor,
            "bundle": build.bundle(subconductor_count=2, subconductor_spacing_in=18),
            "insulator": {
                "insulator_type": "glass", "number_of_insulators": 12,
                "insulator_code": "U120B", "insulator_coupling": "ball_and_socket",
            },
        }],
    )
    line = build.cross_section_line(
        tower, name="3P1", voltage_kv=geometry["voltage_kv"], frequency_hz=60,
        earth_resistivity_ohm_m=100, everyday_tension_fraction=0.2,
    )
    study = build.system(name="st-clair-3p1")
    line = build.add_line(study, line)
    results = build.calculations(
        line,
        st_clair_options={
            "line_length_start_mi": args.length_start_mi,
            "line_length_stop_mi": args.length_stop_mi,
            "line_length_step_mi": args.length_step_mi,
        },
        sag_options={
            "elastic_modulus_psi": 11.5e6,
            "thermal_expansion_per_k": 19.3e-6,
            "span_start_ft": args.span_start_ft,
            "span_stop_ft": args.span_stop_ft,
            "span_step_ft": args.span_step_ft,
        },
        sag_circuit_id=circuit_id,
    )
    if results.skipped or results.impedances is None or results.st_clair is None or results.sag is None:
        raise RuntimeError(f"3P1 calculation incomplete: {results.skipped}")
    electrical = results.impedances
    curve_result = results.st_clair
    sag_result = results.sag

    print(
        f"Tower 3P1 | {geometry['voltage_kv']:g} kV | ACSR Cardinal (54/7) | "
        "2 subconductors at 18 in | Alumoweld 7/8 ground wire"
    )
    _print_sequence_impedances(electrical)
    print(
        "Sequence shunt susceptance (microsiemens/mile): "
        f"b0={electrical.scalars['b0']:.9f}, "
        f"b1={electrical.scalars['b1']:.9f} (St. Clair input)"
    )

    curve = curve_result.curves[0]
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_csv.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(
            [
                "circuit_id",
                "length_mi",
                "pr_mw",
                "ps_mw",
                "current_a",
                "limiting_angle_deg",
                "limit_type",
            ]
        )
        writer.writerows(
            zip(
                [curve.circuit_id] * len(curve.lengths_mi),
                curve.lengths_mi,
                curve.pr_mw,
                curve.ps_mw,
                curve.current_a,
                curve.limiting_angle_deg,
                curve.limit_type,
                strict=True,
            )
        )
    args.output_figure.parent.mkdir(parents=True, exist_ok=True)
    axes = plots.st_clair(curve_result)
    axes.figure.savefig(args.output_figure, dpi=180, bbox_inches="tight")
    plt.close(axes.figure)
    print(
        f"\nSt. Clair curve: {len(curve.lengths_mi)} samples, "
        f"{curve.lengths_mi[0]:g}-{curve.lengths_mi[-1]:g} mi; "
        f"receiving power {curve.pr_mw[0]:.3f}-{curve.pr_mw[-1]:.3f} MW"
    )
    print(f"Curve CSV: {args.output_csv.resolve()}")
    print(f"Curve figure: {args.output_figure.resolve()}")

    sag_curve = sag_result.curves[0]
    args.output_sag_csv.parent.mkdir(parents=True, exist_ok=True)
    with args.output_sag_csv.open("w", newline="", encoding="utf-8") as file_obj:
        writer = csv.writer(file_obj)
        writer.writerow(["span_ft", "sag_ft", "horizontal_tension_lb"])
        writer.writerows(zip(
            sag_curve.span_lengths_ft, sag_curve.sag_ft,
            sag_curve.horizontal_tension_lb, strict=True,
        ))
    args.output_sag_figure.parent.mkdir(parents=True, exist_ok=True)
    axes = plots.sag(sag_result, circuit_id=circuit_id)
    axes.figure.savefig(args.output_sag_figure, dpi=180, bbox_inches="tight")
    plt.close(axes.figure)
    print(
        f"Sag curve: {len(sag_curve.span_lengths_ft)} spans, "
        f"{sag_curve.span_lengths_ft[0]:g}-{sag_curve.span_lengths_ft[-1]:g} ft; "
        f"sag {sag_curve.sag_ft[0]:.3f}-{sag_curve.sag_ft[-1]:.3f} ft"
    )
    print(f"Sag CSV: {args.output_sag_csv.resolve()}")
    print(f"Sag figure: {args.output_sag_figure.resolve()}")


if __name__ == "__main__":
    main()