Serialization
=============

Embedded values
---------------

``LineDataModel`` serializes nested Infrasys quantities to JSON-compatible
values with serialized-type metadata and restores them before Pydantic field
validation. This preserves quantity classes and units across embedded input
model round trips. Standalone result models store matrix values as real and
imaginary numeric arrays with shape, labels, and unit metadata rather than
Python complex values or opaque cells. Calculations return new results without
updating the input components.

Registered system
-----------------

``TransmissionLineSystem`` is an Infrasys ``System`` with package schema
version ``4.0.0``. Use the public Infrasys system serialization methods for the
static input graph so component UUIDs and registered component references are
retained after reload. Older system files are rejected; there is no legacy
upgrade or compatibility adapter. Electrical matrices, St. Clair curves, and
other calculation results are not stored in the system JSON.

The repository tests reload both concrete line types from new-schema system
JSON, verify registered component references, and check that obsolete
calculated fields are absent from the input JSON.
``ElectricalParameters.model_dump_json()`` followed by
``ElectricalParameters.model_validate_json(...)`` checks the standalone result
shape in memory; result-file persistence is not part of system serialization.
When comparing reloaded Pint units, compare unit names or dimensionality
rather than registry-object identity.