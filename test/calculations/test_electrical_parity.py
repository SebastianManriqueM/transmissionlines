import numpy as np
import pytest

from transmissionlines.builders.line import ground_wire_from_record, phase_spec_from_record, geometry_from_records
from transmissionlines.calculations.electrical import calculate_electrical
from transmissionlines.catalog.repository import CatalogRepository
from transmissionlines.catalog.schemas import ConductorRecord, GroundWireRecord, GroundWirePositionRecord, PhasePositionRecord
from transmissionlines.units import Frequency, VoltageKV

CATALOG = CatalogRepository("data/catalog/v1")


def _kersting_inputs():
    code = "EX_K4_1"
    phases = CATALOG.table("phase_positions")
    grounds = CATALOG.table("ground_wire_positions")
    geometry = geometry_from_records(
        [PhasePositionRecord.model_validate(row) for row in phases[phases.geometry_id == code].to_dict("records")],
        [GroundWirePositionRecord.model_validate(row) for row in grounds[grounds.geometry_id == code].to_dict("records")],
    )
    conductors = CATALOG.table("conductors")
    wires = CATALOG.table("ground_wires")
    conductor = conductors[conductors.codeword == "Linnet_EX_K4_1"].iloc[0]
    wire = wires[(wires.family == "ACSR") & (wires.awg_or_stranding == "4/0 6/1")].iloc[0]
    phase = phase_spec_from_record(ConductorRecord.model_validate(conductor.to_dict()), circuit_id="circuit-1", catalog_version="v1")
    ground = ground_wire_from_record(GroundWireRecord.model_validate(wire.to_dict()), catalog_version="v1")
    return geometry, phase, ground


def test_kersting_nontransposed_and_transposed_matrix_outputs() -> None:
    geometry, phase, ground = _kersting_inputs()
    result = calculate_electrical(geometry, phase_specs=[phase], ground_wire_spec=ground, voltage=VoltageKV(33, "kilovolt"), frequency=Frequency(60, "hertz"), earth_resistivity=100.0)

    def matrix(name: str) -> np.ndarray:
        return np.array([[cell["real"] + 1j * cell["imag"] for cell in row] for row in result.matrices[name].cells])

    assert matrix("Zabcg") == pytest.approx(np.array([[.4013+1.4133j, .0953+.8515j, .0953+.7266j, .0953+.7524j], [.0953+.8515j, .4013+1.4133j, .0953+.7802j, .0953+.7865j], [.0953+.7266j, .0953+.7802j, .4013+1.4133j, .0953+.7674j], [.0953+.7524j, .0953+.7865j, .0953+.7674j, .6873+1.5465j]]), rel=0.005)
    assert matrix("Z_kron_nt") == pytest.approx(np.array([[.4576+1.0780j, .1560+.5017j, .1535+.3849j], [.1560+.5017j, .4666+1.0482j, .1580+.4236j], [.1535+.3849j, .1580+.4236j, .4615+1.0651j]]), rel=0.005)
    assert matrix("Z_kron_ft") == pytest.approx(np.array([[.4619+1.0638j, .1558+.4368j, .1558+.4368j], [.1558+.4368j, .4619+1.0638j, .1558+.4368j], [.1558+.4368j, .1558+.4368j, .4619+1.0638j]]), rel=0.005)
    assert matrix("Z012_ft") == pytest.approx(np.diag([.7735+1.9373j, .3061+.6270j, .3061+.6270j]), rel=0.005)
    assert matrix("Y_kron_nt") == pytest.approx(np.array([[5.6711j, -1.8362j, -.7033j], [-1.8362j, 5.9774j, -1.169j], [-.7033j, -1.169j, 5.3911j]]), rel=0.028)
    assert matrix("Z012_nt") == pytest.approx(np.array([[.77354+1.93759j, .02556+.01149j, -.03209+.01589j], [-.03209+.01589j, .30607+.62736j, -.07225-.00603j], [.02556+.01149j, .07230-.00590j, .30607+.62736j]]), rel=0.005)
    assert matrix("Y012_nt") == pytest.approx(np.array([[3.14339j, -.15758-.03302j, .15758-.03302j], [.15758-.03302j, 6.91344j, .82280+.06243j], [-.15758-.03302j, -.82280+.06243j, 6.91344j]]), rel=0.028)
    assert matrix("Y012_ft") == pytest.approx(np.diag([3.14339j, 6.91344j, 6.91344j]), rel=0.028)
    assert result.scalars["surge_impedance_ohm"] == pytest.approx(301.24, rel=0.005)
    assert result.scalars["sil_mw"] == pytest.approx(3.6151, rel=0.005)
    assert result.matrices["Z_kron"] is result.matrices["Z_kron_nt"]
