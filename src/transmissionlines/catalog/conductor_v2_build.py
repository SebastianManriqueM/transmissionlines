"""Generate the PDF-backed conductor table in a separate versioned catalog."""

import json
import shutil
from collections import Counter
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import pandas as pd
import pymupdf

from transmissionlines.catalog.aac_pdf import extract_aac
from transmissionlines.catalog.accc_pdf import extract_accc
from transmissionlines.catalog.acsr_aw_pdf import extract_acsr_aw
from transmissionlines.catalog.acsr_pdf import extract_acsr
from transmissionlines.catalog.acsr_tw_pdf import extract_acsr_tw_areas
from transmissionlines.catalog.acss_hs285_tw_pdf import HS285TWSourceRow, extract_acss_hs285_tw
from transmissionlines.catalog.acss_pdf import extract_acss
from transmissionlines.catalog.acss_tw_pdf import extract_acss_tw_areas
from transmissionlines.catalog.conductor_staging import StagingIssue, stage_sources
from transmissionlines.catalog.conductor_v2 import project_conductor
from transmissionlines.catalog.importer import sha256_file
from transmissionlines.catalog.mechanical_area import resolve_areas
from transmissionlines.catalog.schemas import ConductorFieldProvenance, ConductorV2Record


PINNED_SOURCES = {
    "data/raw/Tower_geometries_DB.xlsx": "e032d8c2f2a78066ceca461270990b02bdb8a91d76e3c83cee47b4d3947bcd0f",
    "data/raw/conductors/southwire/AAC.pdf": "e37d00223b4c1fad5476f8d3e96ec0c08b2f54ae9c06d74c71bd8ff93069abb3",
    "data/raw/conductors/southwire/ACSR.pdf": "8bb6b7e2f0d1448c70f8337dd6ae65796b7cbfa36d145a454bdfba09afd1bf4f",
    "data/raw/conductors/southwire/ACSR_AW.pdf": "16c764ef84bca4c8411d0272ede1d819ef5ff570a99f7bd471f6d99ae2bfa2bd",
    "data/raw/conductors/southwire/ACSR_TW.pdf": "8f5401d9a7fae338bd6562956de7b995edd4dac36c287bf772181aa38f869fcd",
    "data/raw/conductors/southwire/ACSS.pdf": "9babdd90889e32e01ecde6fb7ca628c9456576282001f20d9a559df5e5e3c669",
    "data/raw/conductors/southwire/ACSS TW.pdf": "590cf5d520a113cba11fe9b0d480cdc444d9b528cde8cf0e51f15cdf43b6258b",
    "data/raw/conductors/southwire/ACSS Hs285.pdf": "14dbe01443dd5f3051bc4314527765d8b7ac12e31315e7c9a295201e569a8b9b",
    "data/raw/conductors/ACCC_electrical_data_ctc.pdf": "8f31bcbc7c3fc513b6998fba159045157894831a20b5e5ebf13d0556dad482d3",
}


def _write_table(output: Path, name: str, rows: Iterable[dict[str, Any]], columns: list[str]) -> dict[str, Any]:
    frame = pd.DataFrame.from_records(rows, columns=columns)
    frame.to_parquet(output / f"{name}.parquet", index=False, engine="pyarrow", compression="snappy")
    return {"columns": columns, "row_count": len(frame)}


def _issue_row(issue: StagingIssue) -> dict[str, Any]:
    return {
        "row_key": issue.row_key, "reason": issue.reason, "field": issue.field,
        "source_values": json.dumps([
            {"row_key": row.row_key, "source_sha256": row.source_sha256, "page": row.page,
             "value": str(value)} for row, value in issue.source_values
        ], sort_keys=True),
    }


def _crosswalk(v1: pd.DataFrame, records: list[ConductorV2Record]) -> list[dict[str, Any]]:
    index: dict[tuple[str, str, Decimal, str | None], list[str]] = {}
    for record in records:
        if record.codeword is None or record.size is None:
            continue
        try:
            size = Decimal(record.size)
        except InvalidOperation:
            continue
        key = (record.family, record.codeword.casefold(), size, record.stranding)
        index.setdefault(key, []).append(record.record_id)
    rows: list[dict[str, Any]] = []
    for old in v1.itertuples(index=False):
        excluded = old.family in {"AAAC", "ACAR"}
        matches = [] if excluded or pd.isna(old.size_kcmil) else index.get(
            (old.family, old.codeword.casefold(), Decimal(str(old.size_kcmil)),
             None if pd.isna(old.stranding) else old.stranding), [],
        )
        status = ("excluded_family" if excluded else "mapped" if len(matches) == 1
                  else "ambiguous" if matches else "no_exact_match")
        rows.append({"old_record_id": old.record_id, "new_record_id": matches[0] if len(matches) == 1 else None,
                     "family": old.family, "status": status})
    return sorted(rows, key=lambda row: row["old_record_id"])


def build_conductor_catalog(root: str | Path, output: str | Path) -> dict[str, Any]:
    """Build a deterministic v2 catalog from checked PDFs and existing v1 tables.

    Parameters
    ----------
    root : str or Path
        Repository root containing the raw PDFs and immutable v1 catalog.
    output : str or Path
        New destination directory; existing directories are never overwritten.

    Returns
    -------
    dict[str, Any]
        Source checksums, table schemas, row counts, and version metadata.

    Raises
    ------
    FileExistsError
        If the destination already exists.
    ValueError
        If a PDF adapter changes, conductor identities collide, or staging has
        an unreviewed issue outside the accepted exception inventory.
    """
    root = Path(root)
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    v1 = root / "data/catalog/v1"
    raw = root / "data/raw/conductors"
    southwire = raw / "southwire"
    sources = [
        root / "data/raw/Tower_geometries_DB.xlsx", southwire / "AAC.pdf",
        southwire / "ACSR.pdf", southwire / "ACSR_AW.pdf", southwire / "ACSR_TW.pdf",
        southwire / "ACSS.pdf", southwire / "ACSS TW.pdf", southwire / "ACSS Hs285.pdf",
        raw / "ACCC_electrical_data_ctc.pdf",
    ]
    source_info = []
    for path in sources:
        name = path.relative_to(root).as_posix()
        digest = sha256_file(path)
        if digest != PINNED_SOURCES[name]:
            raise ValueError(f"source checksum mismatch: {name}")
        source_info.append({"path": name, "sha256": digest})
    hs285_rows = extract_acss_hs285_tw(sources[7])
    electrical_index: dict[tuple[str, str | None, str, str | None], HS285TWSourceRow] = {}
    for row in hs285_rows:
        if row.page not in (4, 6):
            continue
        key = (row.section, row.codeword, row.size, row.cells["type_no"].raw)
        if key in electrical_index:
            raise ValueError(f"duplicate HS285 electrical identity: {key}")
        electrical_index[key] = row
    staged = stage_sources(
        aac=extract_aac(sources[1]), acsr=extract_acsr(sources[2]),
        acsr_aw=extract_acsr_aw(sources[3]), acss=extract_acss(sources[5]),
        hs285_tw=hs285_rows, accc=extract_accc(sources[8]),
    )
    resolved = resolve_areas(
        staged, acsr_tw=extract_acsr_tw_areas(sources[4]),
        acss_tw=extract_acss_tw_areas(sources[6]),
    )
    if len(resolved.records) != 641 or any(record.area is None for record in resolved.records):
        raise ValueError("unexpected conductor inventory or missing area")
    accepted = {"tw_area_rounding_difference": 31, "missing_strength": 8, "incompatible_tw_area": 1}
    if dict(Counter(issue.reason for issue in resolved.issues)) != accepted:
        raise ValueError("unreviewed conductor audit findings")
    projected = []
    for record in resolved.records:
        source_row = record.candidate.source
        electrical_row = None
        if record.candidate.family == "ACSS/TW":
            key = (source_row.section, source_row.codeword, source_row.size, source_row.cells["type_no"].raw)
            electrical_row = electrical_index.get(key)
            if electrical_row is None or electrical_row.page != source_row.page + 1:
                raise ValueError(f"missing HS285 electrical match: {key}")
        projected.append(project_conductor(record, electrical_row=electrical_row))
    records = sorted((record for record, _ in projected), key=lambda record: record.record_id)
    if len({record.record_id for record in records}) != len(records):
        raise ValueError("duplicate v2 conductor identity")
    provenance = sorted(
        (item for _, entries in projected for item in entries),
        key=lambda entry: (entry.record_id, entry.field, entry.row_key, entry.source_field),
    )
    manifest_v1 = json.loads((v1 / "manifest.json").read_text(encoding="utf-8"))
    output.mkdir(parents=True)
    tables = {key: value for key, value in manifest_v1["tables"].items() if key != "conductors"}
    for name in tables:
        shutil.copyfile(v1 / f"{name}.parquet", output / f"{name}.parquet")
    tables["conductors"] = _write_table(
        output, "conductors", (record.model_dump(mode="json") for record in records),
        list(ConductorV2Record.model_fields),
    )
    tables["conductor_provenance"] = _write_table(
        output, "conductor_provenance", (entry.model_dump(mode="json") for entry in provenance),
        list(ConductorFieldProvenance.model_fields),
    )
    tables["conductor_issues"] = _write_table(
        output, "conductor_issues", (_issue_row(issue) for issue in sorted(
            resolved.issues, key=lambda issue: (issue.row_key, issue.reason, issue.field))),
        ["row_key", "reason", "field", "source_values"],
    )
    tables["sources"] = _write_table(output, "sources", source_info, ["path", "sha256"])
    tables["conductor_crosswalk"] = _write_table(
        output, "conductor_crosswalk", _crosswalk(pd.read_parquet(v1 / "conductors.parquet"), records),
        ["old_record_id", "new_record_id", "family", "status"],
    )
    for name, metadata in tables.items():
        metadata["sha256"] = sha256_file(output / f"{name}.parquet")
    manifest = {
        "catalog_version": "v2", "schema_version": "4.2.0",
        "extraction_version": "1", "parser_version": pymupdf.VersionBind,
        "sources": source_info, "tables": dict(sorted(tables.items())),
        "normalization": "PDF source row keys and explicit strength variants; no workbook conductor values",
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest