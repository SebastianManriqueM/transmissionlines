Contributing
============

Keep changes within the owning layer: catalog import and exact selection,
typed model construction, pure calculations, and line/system orchestration
have separate boundaries. Preserve public signatures unless an API change is
explicitly intended. Tests should use small in-memory inputs where practical
and should not require unpublished workbooks or manufacturer artifacts.

For documentation changes, verify constructor/function signatures against the
implementation, run the focused example or test first, then run the full test
suite and warnings-as-errors Sphinx HTML and doctest builds. Review the
generated equations, navigation, and cross-references in the HTML artifact.
Do not add generated HTML or build output to version control.