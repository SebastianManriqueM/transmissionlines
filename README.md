# Transmission lines

Python models and tools for transmission-line electrical analysis, tower and route data, engineering catalogs, and dynamic line rating.

## Model packages

- `transmissionlines` contains the electrical-analysis and catalog models.
- `transmissionlines.models` contains the canonical dynamic line rating domain models, including weather sources, rating runs, and span results.

The canonical models use Infrasys `Component` for persisted domain entities, `LineDataModel` for immutable embedded values, and `SupplementalAttribute` for dynamic rating results.

## Install and test

Python 3.12 or newer is required. With [uv](https://docs.astral.sh/uv/):

```bash
uv sync --group dev
uv run pytest
```

## Documentation

- [Catalog schema and workflow](docs/catalog_v3.md)
- [Electrical parity and catalog](docs/electrical_parity_and_catalog.md)
- [Infrasys model foundation](docs/infrasys_foundation_notes.md)
- [DLR domain glossary](CONTEXT.md)
