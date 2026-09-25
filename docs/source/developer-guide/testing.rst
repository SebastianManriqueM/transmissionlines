Testing
-------

Run the full suite from the repository root with:

.. code-block:: console

   uv sync --locked
   uv run pytest

The configured pytest run includes coverage reporting. Focused documentation
examples live in ``test/docs``; the quick-start interactive examples are also
executed by the Sphinx doctest build. Electrical matrix and St. Clair behavior
is covered under ``test/calculations`` and the end-to-end line path under
``test/integration``.

The existing test workflow in ``.github/workflows/tests.yml`` runs the Python
3.12 suite on Linux, macOS, and Windows. The separate documentation workflow
builds HTML with Sphinx warnings treated as errors on pull requests targeting
``main``.
