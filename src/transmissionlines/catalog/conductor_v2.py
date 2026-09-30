"""Project unpublished PDF candidates into v2 conductor and provenance records."""

from transmissionlines.catalog.acsr_pdf import SourceCell
from transmissionlines.catalog.conductor_staging import SourceRow
from transmissionlines.catalog.mechanical_area import AreaCandidate, TWRow
from transmissionlines.catalog.schemas import ConductorFieldProvenance, ConductorV2Record


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
) -> tuple[ConductorV2Record, tuple[ConductorFieldProvenance, ...]]:
    """Project one staged candidate without publishing it or inventing missing fields.

    Parameters
    ----------
    staged : AreaCandidate
        PDF-backed strength candidate and its resolved material area.

    Returns
    -------
    tuple[ConductorV2Record, tuple[ConductorFieldProvenance, ...]]
        A versioned record and one provenance entry per contributing source cell.
    """
    candidate = staged.candidate
    row = candidate.source
    area = staged.area
    record = ConductorV2Record(
        record_id=candidate.record_id, source_id=row.source_sha256,
        family=candidate.family, codeword=candidate.codeword, size=candidate.size,
        variant=candidate.variant, stranding=row.cells["stranding"].raw if "stranding" in row.cells else None,
        diameter_inch=row.numeric("diameter_in") if "diameter_in" in row.cells else None,
        weight_lb_kft=candidate.weight_total_lb_kft,
        rated_strength_lb=candidate.rated_strength_lb,
        aluminum_area_in2=area.aluminum.value if area else None,
        core_area_in2=area.core.value if area and area.core else None,
        total_area_in2=area.total.value if area else None,
        core_diameter_in=row.numeric("core_diameter_in") if "core_diameter_in" in row.cells else None,
    )
    provenance: list[ConductorFieldProvenance] = []
    for field, source_field in (
        ("codeword", "codeword"), ("size", "size"),
        ("stranding", "stranding"), ("diameter_inch", "diameter_in"),
        ("core_diameter_in", "core_diameter_in"),
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