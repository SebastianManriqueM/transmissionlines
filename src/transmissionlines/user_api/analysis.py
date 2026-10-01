"""Run independent cross-section calculations into an external result envelope."""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from pydantic import ValidationError

from transmissionlines.calculations.electrical import calculate_electrical
from transmissionlines.calculations.sag import calculate_sag
from transmissionlines.calculations.st_clair import calculate_st_clair_curve_for_line
from transmissionlines.models.assets import CrossSectionTransmissionLine
from transmissionlines.models.calculation_result import LineCalculationResult
from transmissionlines.models.electrical import ElectricalParameters
from transmissionlines.models.sag import SagCurveResult, SagOptions
from transmissionlines.models.st_clair import StClairOptions, StClairResult
from transmissionlines.units import ElasticModulus, SpanLength, Temperature, ThermalExpansion


@dataclass(frozen=True)
class CrossSectionCalculationResults:
    """Hold optional stored results and reasons for unavailable result groups."""

    line_name: str
    line_uuid: UUID
    configuration_uuid: UUID
    impedances: ElectricalParameters | None = None
    st_clair: StClairResult | None = None
    sag: SagCurveResult | None = None
    skipped: dict[str, str] = field(default_factory=dict)


_SAG_UNITS = {
    "elastic_modulus_psi": ("elastic_modulus", ElasticModulus, "psi"),
    "thermal_expansion_per_k": ("thermal_expansion_coefficient", ThermalExpansion, "1 / kelvin"),
    "span_start_ft": ("span_start", SpanLength, "foot"),
    "span_stop_ft": ("span_stop", SpanLength, "foot"),
    "span_step_ft": ("span_step", SpanLength, "foot"),
    "elevation_difference_ft": ("elevation_difference", SpanLength, "foot"),
    "reference_temperature_c": ("reference_temperature", Temperature, "degC"),
    "operating_temperature_c": ("operating_temperature", Temperature, "degC"),
}


def _sag_options(options: Mapping[str, Any] | SagOptions) -> SagOptions | None:
    if isinstance(options, SagOptions):
        return options
    unknown = set(options) - set(_SAG_UNITS) - {"additional_permanent_strain"}
    if unknown:
        raise ValueError(f"unknown sag_options keys: {sorted(unknown)}")
    converted = {
        field: quantity_type(value, unit)
        for key, (field, quantity_type, unit) in _SAG_UNITS.items()
        if (value := options.get(key)) is not None
    }
    if "additional_permanent_strain" in options:
        converted["additional_permanent_strain"] = options["additional_permanent_strain"]
    try:
        return SagOptions.model_validate(converted)
    except ValidationError as error:
        missing_fields = {"elastic_modulus", "thermal_expansion_coefficient"}
        if error.errors() and all(
            item["type"] == "missing" and item["loc"][0] in missing_fields
            for item in error.errors()
        ):
            return None
        raise


def _missing_electrical(line: CrossSectionTransmissionLine) -> str | None:
    for circuit in line.configuration.circuits:
        equipment = circuit.conductor_spec.equipment
        for field in ("conductor_gmr", "conductor_diameter", "ac_resistance"):
            if getattr(equipment, field) is None:
                return f"circuit {circuit.circuit_id}: missing {field}"
    ground = line.configuration.ground_wire_spec.equipment
    for field in ("conductor_diameter", "dc_resistance"):
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
        for field in ("weight", "rated_breaking_strength", "total_material_area"):
            value = getattr(circuit.conductor_spec.equipment, field)
            if value is None or not math.isfinite(value.magnitude) or value.magnitude <= 0:
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
                voltage=line.nominal_voltage, frequency=line.nominal_frequency,
                earth_resistivity=line.earth_resistivity.to("ohm * meter").magnitude,
            )
        if impedances and missing is not None:
            skipped["impedances"] = missing
        if st_clair:
            if missing is not None:
                skipped["st_clair"] = f"electrical inputs unavailable: {missing}"
            else:
                missing_ampacity = next((
                    circuit.circuit_id for circuit in line.configuration.circuits
                    if circuit.conductor_spec.equipment.ampacity is None
                ), None)
                if missing_ampacity is not None:
                    skipped["st_clair"] = f"circuit {missing_ampacity}: missing ampacity"
                else:
                    previous = LineCalculationResult(
                        line_name=line.name, line_uuid=line.uuid,
                        configuration_uuid=line.configuration.uuid, electrical=electrical,
                    )
                    curve = calculate_st_clair_curve_for_line(line, previous, options=curve_options)
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
        line_name=line.name, line_uuid=line.uuid, configuration_uuid=line.configuration.uuid,
        impedances=electrical if impedances else None, st_clair=curve, sag=sag_result,
        skipped=skipped,
    )