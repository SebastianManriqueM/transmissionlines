# TransmissionLines

[![Tests](https://github.com/SebastianManriqueM/transmissionlines/actions/workflows/tests.yml/badge.svg?branch=main)](https://github.com/SebastianManriqueM/transmissionlines/actions/workflows/tests.yml)
[![Docs build](https://github.com/SebastianManriqueM/transmissionlines/actions/workflows/docs.yml/badge.svg?branch=main)](https://github.com/SebastianManriqueM/transmissionlines/actions/workflows/docs.yml)
[![Documentation](https://img.shields.io/badge/docs-Sphinx-466A7C?logo=sphinx)](https://sebastianmanriquem.github.io/transmissionlines/)

TransmissionLines is a Python package for typed transmission-line models,
electrical parameter calculations, and positive-sequence St. Clair loadability
curves. It requires Python 3.12 or newer and is currently installed
from a repository checkout rather than PyPI.

## Documentation

Read the [documentation overview](https://sebastianmanriquem.github.io/transmissionlines/),
start with the [quick start](https://sebastianmanriquem.github.io/transmissionlines/quickstart.html),
or see the [repository layout and responsibilities](https://sebastianmanriquem.github.io/transmissionlines/developer-guide/repository-layout.html).
The docs workflow builds the Sphinx site and deploys it to
[GitHub Pages](https://sebastianmanriquem.github.io/transmissionlines/). Click the
Docs build badge above to see workflow runs.

## Features

- Typed line, tower, conductor, geometry, routing, and calculation-result models.
- Versioned reference catalogs with validation, exact selection, and provenance.
- Electrical matrices and sequence parameters.
- Balanced positive-sequence St. Clair loadability curves with voltage, ampacity, and stability limits.

## Install

Install `uv`, then run these commands from a checkout:

```console
uv sync --locked
```

## Test

Run the pytest suite, including coverage reporting:

```console
uv run pytest
```

The Tests badge links to the workflow that runs this suite on Python 3.12 across
Linux, macOS, and Windows.

## Build the documentation

Install the documentation dependencies and build the HTML and doctest targets:

```console
uv sync --locked --group docs
uv run sphinx-build -W --keep-going -b html docs/source docs/build/html
uv run sphinx-build -W --keep-going -b doctest docs/source docs/build/doctest
```

The Docs build badge links to the workflow that runs these checks on pull
requests to `main` and pushes to `main`.

## Contributing

See the [developer guide](docs/source/developer-guide/index.rst) for
documentation, testing, and contribution workflows.
