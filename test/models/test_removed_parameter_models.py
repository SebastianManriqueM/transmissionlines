import importlib

import pytest

from transmissionlines import models
from transmissionlines.builders import line as line_builder


@pytest.mark.parametrize(
    "module_name",
    [
        "transmissionlines.models.parameters",
        "transmissionlines.models.mechanical",
    ],
)
def test_obsolete_parameter_model_modules_are_removed(module_name: str) -> None:
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


def test_obsolete_parameter_models_are_not_exported() -> None:
    assert "LineParameters" not in models.__all__
    assert "MechanicalParameters" not in models.__all__
    assert not hasattr(models, "LineParameters")
    assert not hasattr(models, "MechanicalParameters")


def test_unused_electrical_parameter_replacement_helper_is_removed() -> None:
    assert "replace_electrical_parameters" not in line_builder.__all__
    assert not hasattr(line_builder, "replace_electrical_parameters")
