"""Run independent cross-section calculations into an external result envelope."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from transmissionlines.calculations.electrical import calculate_electrical, calculate_st_clair_curve_for_line
from transmissionlines.calculations.sag import calculate_sag
from transmissionlines.models.assets import CrossSectionTransmissionLine
from transmissionlines.models.electrical import ElectricalParameters
from transmissionlines.models.sag import SagCurveResult, SagOptions
from transmissionlines.models.st_clair import StClairOptions, StClairResult


@dataclass(frozen=True)
class CrossSectionCalculationResults:
    """Hold optional stored results and reasons for unavailable result groups."""

    line_name: str
    impedances: ElectricalParameters | None = None
    st_clair: StClairResult | None = None
    sag: SagCurveResult | None = None
    skipped: dict[str, str] = field(default_factory=dict)


def _sag_options(options: Mapping[str, Any] | SagOptions) -> SagOptions | None:
    if isinstance(options, SagOptions):
        return options
    unknown = set(options) - set(SagOptions.model_fields)
    if unknown:
        raise ValueError(f"unknown sag_options keys: {sorted(unknown)}")
    try:
        return SagOptions.model_validate({key: value for key, value in options.items() if value is not None})
    except ValidationError as error:
        missing_fields = {"elastic_modulus_psi", "thermal_expansion_per_k"}
        if error.errors() and all(
            item["type"] == "missing" and item["loc"][0] in missing_fields
            for item in error.errors()
        ):
            return None
        raise


def _missing_electrical(line: CrossSectionTransmissionLine) -> str | None:
    for circuit in line.configuration.circuits:
        equipment = circuit.conductor_spec.equipment
        for field in ("gmr_ft", "diameter_in", "ac_resistance_ohm_kft"):
            if getattr(equipment, field) is None:
                return f"circuit {circuit.circuit_id}: missing {field}"
    ground = line.configuration.ground_wire_spec.equipment
    for field in ("diameter_in", "dc_resistance_ohm_kft"):
        if getattr(ground, field) is None:
            return f"ground wire: missing {field}"
    return None


def _missing_sag(line: CrossSectionTransmissionLine, circuit_id: str | None) -> str | None:
    circuits = line.configuration.circuits
    if circuit_id is not None:
        circuits = [circuit for circuit in circuits if circuit.circuit_id == circuit_id]
        if not circuits:
            raise ValueError(f"unknown sag_circuit_id {circuit_id!r}")
    for circuit in circuits:
        for field in ("weight_lb_kft", "rated_strength_lb", "total_area_in2"):
            if getattr(circuit.conductor_spec.equipment, field) is None:
                return f"circuit {circuit.circuit_id}: missing {field}"
    return None


def calculations(
    line: CrossSectionTransmissionLine, *, impedances: bool = True,
    st_clair: bool = True, sag: bool = True,
    st_clair_options: Mapping[str, Any] | StClairOptions | None = None,
    sag_options: Mapping[str, Any] | SagOptions | None = None,
    sag_circuit_id: str | None = None,
) -> CrossSectionCalculationResults:
    """Calculate requested available results without changing the input graph.

    Parameters
    ----------
    line : CrossSectionTransmissionLine
        Standalone or registered cross-section input.
    impedances, st_clair, sag : bool, optional
        Independently enable the electrical, loadability, and sag result groups.
    st_clair_options : mapping or StClairOptions, optional
        Existing St. Clair option fields or a validated options object.
    sag_options : mapping or SagOptions, optional
        Unit-suffixed effective material and hypothetical span settings.
    sag_circuit_id : str, optional
        Select one circuit for sag; otherwise process all eligible circuits.

    Returns
    -------
    CrossSectionCalculationResults
        External results and field-specific skipped reasons.
    """
    if not isinstance(line, CrossSectionTransmissionLine):
        raise TypeError("calculations requires a CrossSectionTransmissionLine")
    if not st_clair and st_clair_options is not None:
        raise ValueError("st_clair_options provided for disabled st_clair")
    if not sag and (sag_options is not None or sag_circuit_id is not None):
        raise ValueError("sag options provided for disabled sag")
    if st_clair_options is None:
        curve_options = StClairOptions()
    elif isinstance(st_clair_options, StClairOptions):
        curve_options = st_clair_options
    else:
        curve_options = StClairOptions.model_validate(st_clair_options)
    sag_settings = None if sag_options is None else _sag_options(sag_options)
    skipped: dict[str, str] = {}
    electrical = curve = sag_result = None
    if impedances or st_clair:
        missing = _missing_electrical(line)
        if missing is None:
            configuration = line.configuration
            electrical = calculate_electrical(
                configuration.geometry, phase_specs=configuration.circuits,
                ground_wire_spec=configuration.ground_wire_spec,
                voltage_kv=line.nominal_voltage_kv, frequency_hz=line.nominal_frequency_hz,
                earth_resistivity_ohm_m=line.earth_resistivity_ohm_m,
            )
        if impedances and missing is not None:
            skipped["impedances"] = missing
        if st_clair:
            if missing is not None:
                skipped["st_clair"] = f"electrical inputs unavailable: {missing}"
            else:
                missing_ampacity = next((
                    circuit.circuit_id for circuit in line.configuration.circuits
                    if circuit.conductor_spec.equipment.ampacity_a is None
                ), None)
                if missing_ampacity is not None:
                    skipped["st_clair"] = f"circuit {missing_ampacity}: missing ampacity"
                else:
                    curve = calculate_st_clair_curve_for_line(line, options=curve_options)
    if not impedances:
        skipped["impedances"] = "disabled"
    if not st_clair:
        skipped["st_clair"] = "disabled"
    if sag:
        missing_sag = _missing_sag(line, sag_circuit_id)
        if sag_settings is None:
            absent = [
                key for key in ("elastic_modulus_psi", "thermal_expansion_per_k")
                if sag_options is None or sag_options.get(key) is None
            ]
            skipped["sag"] = f"missing {', '.join(absent)} in sag_options"
        elif missing_sag is not None:
            skipped["sag"] = missing_sag
        else:
            sag_result = calculate_sag(line, options=sag_settings, circuit_id=sag_circuit_id)
    else:
        skipped["sag"] = "disabled"
    return CrossSectionCalculationResults(
        line_name=line.name,
        impedances=electrical if impedances else None, st_clair=curve, sag=sag_result,
        skipped=skipped,
    )