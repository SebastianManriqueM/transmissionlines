"""Calculate and export St. Clair and sequence impedances for tower 3P1.

Run from the repository root with::

    python scripts/st_clair_3p1.py --output-csv st_clair_3p1_curve.csv

The example uses Cardinal ACSR (54/7, 1.196 in), two subconductors per phase
at 18-inch spacing, and the Alumoweld 7/8 ground wire from the parity tests.
The input graph also records an assumed 12-unit glass U120B insulator string.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from transmissionlines.builders.line import (
    geometry_from_records,
    ground_wire_from_record,
    phase_spec_from_record,
)
from transmissionlines.api import assemble_line_into_system, calculate_line_electrical_parameters
from transmissionlines.catalog.repository import CatalogRepository
from transmissionlines.catalog.schemas import (
    ConductorRecord,
    GroundWireRecord,
    GroundWirePositionRecord,
    PhasePositionRecord,
)
from transmissionlines.models.assets import CrossSectionTransmissionLine
from transmissionlines.models.cables import InsulatorStringSpec
from transmissionlines.models.common import IdentificationInfo
from transmissionlines.models.configurations import TowerConfiguration
from transmissionlines.models.electrical import ElectricalParameters
from transmissionlines.models.st_clair import StClairOptions
from transmissionlines.plotting.st_clair import plot_st_clair_curve
from transmissionlines.system import TransmissionLineSystem
from transmissionlines.units import BundleSpacing, EarthResistivity, Frequency, VoltageKV


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog-path",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "catalog" / "v1",
        help="normalized catalog directory (default: repository data/catalog/v1)",
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
    parser.add_argument("--length-start-mi", type=float, default=20.0)
    parser.add_argument("--length-stop-mi", type=float, default=600.0)
    parser.add_argument("--length-step-mi", type=float, default=20.0)
    return parser.parse_args()


def _print_sequence_impedances(electrical: ElectricalParameters) -> None:
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
    catalog = CatalogRepository(args.catalog_path, catalog_version="v1")

    tower = catalog.select_exact("tower_geometries", structure_code="3P1")
    phase_positions = catalog.table("phase_positions")
    ground_positions = catalog.table("ground_wire_positions")
    geometry_id = tower["record_id"]
    geometry = geometry_from_records(
        [
            PhasePositionRecord.model_validate(row)
            for row in phase_positions[
                phase_positions.geometry_id == geometry_id
            ].to_dict("records")
        ],
        [
            GroundWirePositionRecord.model_validate(row)
            for row in ground_positions[
                ground_positions.geometry_id == geometry_id
            ].to_dict("records")
        ],
    )

    conductor = ConductorRecord.model_validate(
        catalog.select_exact("conductors", family="ACSR", codeword="Cardinal")
    )
    ground_wire = GroundWireRecord.model_validate(
        catalog.select_exact(
            "ground_wires", family="Alumoweld", awg_or_stranding="7/8"
        )
    )
    phase_spec = phase_spec_from_record(
        conductor,
        circuit_id="circuit-1",
        subconductor_count=2,
        subconductor_spacing=BundleSpacing(18, "inch"),
        insulator_string=InsulatorStringSpec(
            insulator_type="glass",
            number_of_insulators=12,
            insulator_code="U120B",
            insulator_coupling="ball_and_socket",
        ),
        catalog_version="v1",
    )
    ground_spec = ground_wire_from_record(ground_wire, catalog_version="v1")
    voltage_kv = float(tower["voltage_kv"])
    configuration = TowerConfiguration(
        name=f"v1:tower-configuration:{geometry_id}",
        identification_info=IdentificationInfo(
            geometry_id=geometry_id,
            structure_code="3P1",
        ),
        geometry=geometry,
        ground_wire_spec=ground_spec,
        circuits=[phase_spec],
    )
    line = CrossSectionTransmissionLine(
        name="3P1",
        configuration=configuration,
        nominal_voltage=VoltageKV(voltage_kv, "kilovolt"),
        nominal_frequency=Frequency(60, "hertz"),
        earth_resistivity=EarthResistivity(100, "ohm * meter"),
    )
    system = TransmissionLineSystem(name="st-clair-3p1")
    registered_line = assemble_line_into_system(system, line)

    options = StClairOptions(
        line_length_start_mi=args.length_start_mi,
        line_length_stop_mi=args.length_stop_mi,
        line_length_step_mi=args.length_step_mi,
    )
    calculation = calculate_line_electrical_parameters(
        registered_line,
        st_clair_options=options,
    )
    electrical = calculation.electrical
    if calculation.st_clair is None:
        raise RuntimeError("line calculation did not return a St. Clair result")
    curve_result = calculation.st_clair

    print(
        f"Tower 3P1 | {voltage_kv:g} kV | ACSR {conductor.codeword} "
        f"({conductor.stranding}, {conductor.diameter_inch:.3f} in) | "
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
    axes = plot_st_clair_curve(curve_result, y="pr_mw", show_limits=True)
    axes.figure.savefig(args.output_figure, dpi=180, bbox_inches="tight")
    print(
        f"\nSt. Clair curve: {len(curve.lengths_mi)} samples, "
        f"{curve.lengths_mi[0]:g}-{curve.lengths_mi[-1]:g} mi; "
        f"receiving power {curve.pr_mw[0]:.3f}-{curve.pr_mw[-1]:.3f} MW"
    )
    print(f"Curve CSV: {args.output_csv.resolve()}")
    print(f"Curve figure: {args.output_figure.resolve()}")


if __name__ == "__main__":
    main()