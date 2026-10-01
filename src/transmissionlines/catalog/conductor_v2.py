"""Project unpublished PDF candidates into v2 conductor and provenance records."""

from decimal import Decimal

from transmissionlines.catalog.acsr_pdf import SourceCell
from transmissionlines.catalog.acss_hs285_tw_pdf import HS285TWSourceRow
from transmissionlines.catalog.conductor_staging import SourceRow
from transmissionlines.catalog.mechanical_area import AreaCandidate, TWRow
from transmissionlines.catalog.schemas import ConductorFieldProvenance, ConductorV2Record


_ELECTRICAL_FIELDS = (
    "dc_resistance_20c_ohm_kft", "ac_resistance_25c_ohm_kft",
    "ac_resistance_50c_ohm_kft", "ac_resistance_75c_ohm_kft",
    "ac_resistance_200c_ohm_kft", "ampacity_75c_a", "ampacity_100c_a",
    "ampacity_150c_a", "ampacity_180c_a", "ampacity_200c_a", "ampacity_250c_a",
)
_FEET_PER_MILE_IN_KFT = Decimal("5.28")


def _provenance(
    *, record_id: str, field: str, row: SourceRow | TWRow, source_field: str,
    cell: SourceCell, method: str, input_fields: tuple[str, ...] = (), note: str = "",
) -> ConductorFieldProvenance:
    return ConductorFieldProvenance(
        record_id=record_id, field=field, method=method,
        source_id=row.source_sha256, row_key=row.row_key,
        source_sha256=row.source_sha256, page=row.page,
        source_field=source_field, source_header=cell.header,
        raw_value=cell.raw, unit=cell.unit, input_fields=input_fields, note=note,
    )


def project_conductor(
    staged: AreaCandidate,
    *, electrical_row: HS285TWSourceRow | None = None,
) -> tuple[ConductorV2Record, tuple[ConductorFieldProvenance, ...]]:
    """Project one staged candidate without publishing it or inventing missing fields.

    Parameters
    ----------
    staged : AreaCandidate
        PDF-backed strength candidate and its resolved material area.
    electrical_row : HS285TWSourceRow, optional
        Paired shaped-wire electrical page, when verified by codeword, size,
        type, and layout.

    Returns
    -------
    tuple[ConductorV2Record, tuple[ConductorFieldProvenance, ...]]
        A versioned record and one provenance entry per contributing source cell.
    """
    candidate = staged.candidate
    row = candidate.source
    area = staged.area
    rating_row = electrical_row if electrical_row is not None else row
    core_strand_field = {
        "ACSR": "strand_diameter_stl_in", "ACSR/AW": "strand_diameter_aw_in",
        "ACSS": "strand_diameter_steel_in",
    }.get(candidate.family)
    electrical: dict[str, Decimal] = {}
    electrical_sources: dict[str, str] = {}
    for field in _ELECTRICAL_FIELDS:
        source_field = field if field in rating_row.cells else field.replace("_ohm_kft", "_ohm_mile")
        if source_field not in rating_row.cells:
            continue
        value = rating_row.numeric(source_field)
        if value is not None:
            electrical[field] = value / _FEET_PER_MILE_IN_KFT if source_field != field else value
            electrical_sources[field] = source_field
    ac_temperatures = [int(field.split("_")[2][:-1]) for field in electrical if field.startswith("ac_resistance_")]
    ampacity_temperatures = [int(field.split("_")[1][:-1]) for field in electrical if field.startswith("ampacity_")]
    record = ConductorV2Record(
        record_id=candidate.record_id, source_id=row.source_sha256,
        family=candidate.family, codeword=candidate.codeword, size=candidate.size,
        variant=candidate.variant, stranding=row.cells["stranding"].raw if "stranding" in row.cells else None,
        gmr_ft=rating_row.numeric("gmr_ft") if "gmr_ft" in rating_row.cells else None,
        diameter_inch=row.numeric("diameter_in") if "diameter_in" in row.cells else None,
        weight_lb_kft=candidate.weight_total_lb_kft,
        rated_strength_lb=candidate.rated_strength_lb,
        aluminum_area_in2=area.aluminum.value if area else None,
        core_area_in2=area.core.value if area and area.core else None,
        total_area_in2=area.total.value if area else None,
        core_diameter_in=row.numeric("core_diameter_in") if "core_diameter_in" in row.cells else None,
        strand_diameter_al_in=row.numeric("strand_diameter_al_in") if "strand_diameter_al_in" in row.cells else None,
        strand_diameter_core_in=row.numeric(core_strand_field) if core_strand_field in row.cells else None,
        ac_resistance_temperature_c=ac_temperatures[0] if len(ac_temperatures) == 1 else None,
        ampacity_temperature_c=ampacity_temperatures[0] if len(ampacity_temperatures) == 1 else None,
        **electrical,
    )
    provenance: list[ConductorFieldProvenance] = []
    for field, source_field in (
        ("codeword", "codeword"), ("size", "size"),
        ("stranding", "stranding"), ("diameter_inch", "diameter_in"),
        ("core_diameter_in", "core_diameter_in"),
        ("strand_diameter_al_in", "strand_diameter_al_in"),
        ("strand_diameter_core_in", core_strand_field),
    ):
        if getattr(record, field) is not None and source_field in row.cells:
            provenance.append(_provenance(
                record_id=record.record_id, field=field, row=row,
                source_field=source_field, cell=row.cells[source_field], method="published",
            ))
    for field, cell, method in (
        ("rated_strength_lb", candidate.strength_cell, "published"),
        ("weight_lb_kft", candidate.weight_cell,
         "assumed" if candidate.weight_basis == "shared_approximation" else "published"),
    ):
        value = getattr(record, field)
        if value is not None:
            source_field = next(key for key, source_cell in row.cells.items() if source_cell is cell)
            provenance.append(_provenance(
                record_id=record.record_id, field=field, row=row,
                source_field=source_field, cell=cell, method=method,
                note="Standard weight shared with ULS" if method == "assumed" else "",
            ))
    for field, source_field in electrical_sources.items():
        provenance.append(_provenance(
            record_id=record.record_id, field=field, row=rating_row,
            source_field=source_field, cell=rating_row.cells[source_field],
            method="derived" if source_field != field else "published",
            note="Divide ohm/mile by 5.28 to obtain ohm/kft" if source_field != field else "",
        ))
    if record.gmr_ft is not None:
        provenance.append(_provenance(
            record_id=record.record_id, field="gmr_ft", row=rating_row,
            source_field="gmr_ft", cell=rating_row.cells["gmr_ft"], method="published",
        ))
    if area is not None:
        for field, value in (
            ("aluminum_area_in2", area.aluminum),
            ("core_area_in2", area.core),
            ("total_area_in2", area.total),
        ):
            if value is None:
                continue
            input_fields = tuple(item.field for item in value.input_cells)
            source_row = value.source_rows[0]
            for item in value.input_cells:
                provenance.append(_provenance(
                    record_id=record.record_id, field=field, row=source_row,
                    source_field=item.field, cell=item.cell, method=value.method,
                    input_fields=input_fields, note=value.note,
                ))
    return record, tuple(provenance)