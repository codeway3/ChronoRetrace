import sys


def test_python_version_is_3_10():
    assert sys.version_info[:2] == (3, 10), (
        f"Python 3.10 required for CI; found {sys.version}. "
        "Ensure actions/setup-python uses 3.10 and local venv is created with python3.10."
    )