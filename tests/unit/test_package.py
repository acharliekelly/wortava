import wortava


def test_package_exposes_version() -> None:
    assert wortava.__version__ == "0.1.0"
