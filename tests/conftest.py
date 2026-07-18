import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-windows-package",
        action="store_true",
        default=False,
        help="run tests requiring dist/wortava/wortava.exe",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-windows-package"):
        return
    skip = pytest.mark.skip(reason="requires --run-windows-package")
    for item in items:
        if "windows_package" in item.keywords:
            item.add_marker(skip)
