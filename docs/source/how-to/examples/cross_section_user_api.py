"""Run a catalog-backed cross-section study with only two everyday imports."""

from transmissionlines.user_api import build, plots

catalog = build.open_catalog()
tower_choices = catalog.towers(structure_code="3L11", n_circuits=2, n_ground_wires=2)
conductor_choices = catalog.conductors(
    family="ACSS/TW", gmr_available=True, ampacity_75c_min_a=1000,
)
wire_choices = catalog.ground_wires(family="ACSR", diameter_min_in=0.25)

# Inspect catalog.format_choices(...) before fixing these exact selections for a study.
geometry_id = tower_choices[0]["record_id"]
conductor_id = "ACSS/HS285/TW:area-equal:1033.5:curlew:type-13:standard"
ground_wire_id = wire_choices[0]["record_id"]
assert conductor_id in {choice["record_id"] for choice in conductor_choices}

conductor = build.conductor(catalog, record_id=conductor_id)
ground_wire = build.ground_wire(catalog, record_id=ground_wire_id)
bundle = build.bundle(subconductor_count=2, subconductor_spacing_in=18)
insulator = {
    "insulator_type": "glass", "number_of_insulators": 12,
    "insulator_code": "U120B", "insulator_coupling": "ball_and_socket",
}
circuit_ids = catalog.tower_circuits(geometry_id)
tower = build.tower(
    catalog, name="reference-tower", geometry_id=geometry_id, ground_wire=ground_wire,
    circuits=[
        {"circuit_id": circuit_id, "conductor": conductor, "bundle": bundle, "insulator": insulator}
        for circuit_id in circuit_ids
    ],
)
line = build.cross_section_line(
    tower, name="reference-cross-section", voltage_kv=230, frequency_hz=60,
    earth_resistivity_ohm_m=100, everyday_tension_fraction=0.20,
)
study = build.system(name="study")
line = build.add_line(study, line)
results = build.calculations(
    line,
    st_clair_options={"line_length_stop_mi": 20},
    sag_options={
        "elastic_modulus_psi": 11.5e6, "thermal_expansion_per_k": 19.3e-6,
        "span_start_ft": 100, "span_stop_ft": 200, "span_step_ft": 50,
    },
)
if results.impedances is not None:
    per_circuit = results.impedances.circuit_scalars[circuit_ids[0]]
    sequence_matrix = results.impedances.matrices["Z012_ft"]
if results.st_clair is not None:
    loadability_axes = plots.st_clair(results.st_clair)
if results.sag is not None:
    sag_axes = plots.sag(results.sag, circuit_id=circuit_ids[0])

print(f"{len(circuit_ids)} circuits")
print(f"{len(results.sag.curves)} sag curves" if results.sag else "0 sag curves")
print(f"{len(results.skipped)} skipped")