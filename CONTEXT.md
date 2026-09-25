# Domain glossary

## Identity

Each persisted domain object is identified by its Infrasys UUID. A name is a
human-readable label, not a separate identifier; composition objects without a
meaningful label use an empty name and still receive a UUID.

## Transmission line

An electrical asset composed of an ordered, continuous chain of line spans. Its
physical route and endpoints are defined by those spans and their support
structures.

## Line span

A conductor route between two distinct support structures. Its geometry may
contain multiple connected or disjoint line segments. The conductor normally
comes from the towers' shared configuration; a span-specific conductor is an
exception for the uncommon case where the installed design changes between
supports.

## Tower configuration

A reusable electrical arrangement carried by one or more support structures.
It describes circuit and phase bundling and the default conductor design.

## Conductor design

A reusable conductor specification composed from separate mechanical,
electrical, and thermal parameter sets. These parameter sets can be shared by
multiple conductor designs when their values match.

## Weather station and weather time series

A geographic source for weather time series. Ambient temperature, eastward and
northward wind velocity, and solar irradiance are time-varying inputs, not
static station attributes.

## Thermal rating parameters

Reusable operating limits for the conductor-temperature constraint applied by
a rating calculation.

## Dynamic line rating run

A versioned calculation instance for a transmission line, with the weather
time-series sources and thermal limits used as inputs.

## Dynamic line rating result

A time-valid span current rating produced by a run. A result tracks its run,
rated span, and weather source through component associations. A line-level
rating can be derived from its span ratings rather than duplicated.
