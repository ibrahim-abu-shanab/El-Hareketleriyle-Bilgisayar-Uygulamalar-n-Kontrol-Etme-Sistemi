"""Enforces the Clean Architecture dependency rule: domain <- application <- infrastructure."""

import ast
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "jestkontrol"
PACKAGE = "jestkontrol"

FORBIDDEN_IMPORTS: dict[str, tuple[str, ...]] = {
    "domain": (f"{PACKAGE}.application", f"{PACKAGE}.infrastructure", f"{PACKAGE}.bootstrap"),
    "application": (f"{PACKAGE}.infrastructure", f"{PACKAGE}.bootstrap"),
    "infrastructure": (f"{PACKAGE}.bootstrap",),
    "ui": (f"{PACKAGE}.infrastructure", f"{PACKAGE}.bootstrap"),
}
THIRD_PARTY_FREE_LAYERS = ("domain", "application")


def imported_modules(path: Path) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


def layer_files(layer: str) -> list[Path]:
    return sorted((SOURCE_ROOT / layer).rglob("*.py"))


@pytest.mark.parametrize("layer", FORBIDDEN_IMPORTS)
def test_layer_does_not_import_outer_layers(layer):
    violations = [
        f"{path.relative_to(SOURCE_ROOT)} imports {module}"
        for path in layer_files(layer)
        for module in imported_modules(path)
        if module.startswith(FORBIDDEN_IMPORTS[layer])
    ]

    assert violations == []


@pytest.mark.parametrize("layer", THIRD_PARTY_FREE_LAYERS)
def test_inner_layers_only_use_stdlib_and_own_package(layer):
    stdlib = set(__import__("sys").stdlib_module_names)
    violations = [
        f"{path.relative_to(SOURCE_ROOT)} imports {module}"
        for path in layer_files(layer)
        for module in imported_modules(path)
        if module.split(".")[0] not in stdlib | {PACKAGE}
    ]

    assert violations == []
