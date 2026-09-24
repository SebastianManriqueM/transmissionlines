"""Exact state and catalog selection helpers."""

from typing import Any

from transmissionlines.catalog.repository import CatalogRepository


def select_state(repository: CatalogRepository, selector: str) -> dict[str, Any]:
    """Select one state using an exact canonical identity."""
    return repository.select_state(selector)


def expand_states(repository: CatalogRepository, selector: str) -> list[str]:
    """Return the selected state and exact border neighbors."""
    state = repository.select_state(selector)
    result = [state["code"]]
    try:
        borders = repository.table("state_borders")
    except FileNotFoundError:
        return result
    for column in (("state_code", "border_state_code"), ("from_state", "to_state")):
        if all(name in borders for name in column):
            for _, row in borders.iterrows():
                if row[column[0]] == state["code"]:
                    result.append(row[column[1]])
                elif row[column[1]] == state["code"]:
                    result.append(row[column[0]])
            break
    return list(dict.fromkeys(result))


__all__ = ["expand_states", "select_state"]
