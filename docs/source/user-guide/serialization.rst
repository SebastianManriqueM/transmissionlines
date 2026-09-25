Serialization
=============

Embedded values
---------------

``LineDataModel`` serializes nested Infrasys quantities to JSON-compatible
values with serialized-type metadata and restores them before Pydantic field
validation. This preserves quantity classes and units across embedded model
round trips. Matrix values use real and imaginary numeric arrays plus shape,
labels, and unit metadata rather than Python complex values or opaque cells.
The result models are immutable; calculations replace values by creating
copies.

Registered system
-----------------

``TransmissionLineSystem`` is an Infrasys ``System`` with package schema
version ``3.0.0``. Use the public Infrasys system serialization methods for a
complete model graph so component UUIDs and component references are retained.
After deserialization, the system resolves the line's nested bus copies to the
registered bus instances. The foundation supports metadata-only upgrades from
the listed legacy schemas and rejects unsupported versions; it does not claim
to migrate arbitrary legacy payloads.

Useful round-trip checks in the repository include
``ElectricalParameters.model_dump_json()`` followed by
``ElectricalParameters.model_validate_json(...)`` and system-level JSON tests
under ``test/models``. When comparing reloaded Pint units, compare unit names or
dimensionality rather than registry-object identity.