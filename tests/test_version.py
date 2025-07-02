from pathlib import Path

import toml

HERE = Path(__file__).parent
PYPROJECT_TOML_PATH = HERE.parent / "pyproject.toml"


def test___version__():
    from exiftool_wrapper.version import __version__

    pyproject = toml.load(PYPROJECT_TOML_PATH)

    assert __version__ == pyproject["project"]["version"]
