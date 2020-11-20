import filecmp
import os
import pathlib
import pytest
import re
import shutil
import subprocess


# Regular expression taken from
# https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case/1176023#1176023
TO_SNAKE_CASE_REGEX = re.compile(r"(?<!^)(?=[A-Z])")


def to_snake_case(camel_case_name: str) -> str:
    return TO_SNAKE_CASE_REGEX.sub("_", camel_case_name).lower()


def to_path(qualified_camel_case_name: str) -> pathlib.Path:
    return pathlib.Path("tests") / pathlib.Path(
        *(to_snake_case(name) for name in qualified_camel_case_name.split("."))
    )


@pytest.fixture
def directory_path(request) -> pathlib.Path:
    return to_path(request.function.__qualname__)


def compare_with_expected_file(directory_path, file_name):
    actual_file_path = directory_path / "actual_output" / file_name
    expected_file_path = directory_path / "expected_output" / file_name
    return filecmp.cmp(actual_file_path, expected_file_path, shallow=False)


def assert_equality_with_expected_files(directory_path, file_names):
    results = [
        (file_name, compare_with_expected_file(directory_path, file_name))
        for file_name in file_names
    ]
    assert results == [(file_name, True) for file_name in file_names]


def run(command):
    print(f"about to run the command `{command}`")
    completed_process = subprocess.run(command, shell=True, capture_output=True)
    assert completed_process.stderr == b""
    assert completed_process.returncode == 0
    return completed_process.stdout


class TestTrace:
    class TestIntegration:
        @pytest.fixture(autouse=True)
        def clean_up(self, directory_path) -> None:
            shutil.rmtree(directory_path / "actual_output")
            shutil.rmtree(directory_path / "workDir")
            yield

        def test_simple(self, directory_path) -> None:
            run(f"python3 ./glare/trace.py {directory_path}/config.ini -c 5 -ab 0")
            assert_equality_with_expected_files(
                directory_path,
                [
                    "fDGPe_0.out",
                    "dgp_0.out",
                    "time.out",
                ],
            )
