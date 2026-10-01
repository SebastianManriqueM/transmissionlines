"""Build and calculate a two-circuit cross-section with the public user API."""

from transmissionlines.user_api import build


def build_line():
    """Build the representative 3L11 line from exact v2 catalog selections."""
    catalog = build.open_catalog()
    tower_row = catalog.towers(structure_code="3L11")[0]
    geometry_id = tower_row["record_id"]
    conductor = build.conductor(catalog, record_id="ACSR:954:cardinal:standard:54/7")
    ground_wire = build.ground_wire(catalog, record_id="Alumoweld:7/7:145.7:15")
    insulator = {
        "insulator_type": "glass", "number_of_insulators": 12,
        "insulator_code": "U120B", "insulator_coupling": "ball_and_socket",
    }
    tower = build.tower(
        catalog, geometry_id=geometry_id, name="3L11-cardinal", ground_wire=ground_wire,
        circuits=[{
            "circuit_id": circuit_id, "conductor": conductor,
            "bundle": build.bundle(subconductor_count=1), "insulator": insulator,
        } for circuit_id in catalog.tower_circuits(geometry_id)],
    )
    return build.cross_section_line(
        tower, name="3L11-example", voltage_kv=tower_row["voltage_kv"],
        frequency_hz=60, earth_resistivity_ohm_m=100,
    )


if __name__ == "__main__":
    line = build_line()
    result = build.calculations(
        line, st_clair_options={"line_length_start_mi": 20, "line_length_stop_mi": 20},
        sag=False,
    )
    print(result.impedances.status)
    print(len(result.st_clair.curves))