import filecmp
import pathlib
import pytest
import re
import shutil
import subprocess
import typing


# Regular expression taken from
# https://stackoverflow.com/questions/1175208/elegant-python-function-to-convert-camelcase-to-snake-case/1176023#1176023
TO_SNAKE_CASE_REGEX = re.compile(r"(?<!^)(?=[A-Z])")  # type: typing.Pattern[str]


def to_snake_case(camel_case_name: str) -> str:
    return TO_SNAKE_CASE_REGEX.sub("_", camel_case_name).lower()


def to_path(qualified_camel_case_name: str) -> pathlib.Path:
    return pathlib.Path("tests") / pathlib.Path(
        *(to_snake_case(name) for name in qualified_camel_case_name.split("."))
    )


# `request` is of type
# https://docs.pytest.org/en/latest/reference.html#pytest.fixtures.FixtureRequest
# However, using `pytest.fixtures.FixtureRequest` instead of `Any` results in the error
# "AttributeError: module 'pytest' has no attribute 'fixtures'".
@pytest.fixture
def test_directory_path(request: typing.Any) -> pathlib.Path:
    return to_path(request.function.__qualname__)


def compare_with_expected_file(
    test_directory_path: pathlib.Path,  # pylint: disable=redefined-outer-name
    file_name: str,
) -> bool:
    actual_file_path = test_directory_path / "actual_output" / file_name
    expected_file_path = test_directory_path / "expected_output" / file_name
    return filecmp.cmp(str(actual_file_path), str(expected_file_path), shallow=False)


def assert_equality_of_actual_and_expected_output(  # pylint: disable=invalid-name
    test_directory_path: pathlib.Path,  # pylint: disable=redefined-outer-name
    file_names: typing.List[str],
) -> None:
    results = [
        (file_name, compare_with_expected_file(test_directory_path, file_name))
        for file_name in file_names
    ]
    assert results == [(file_name, True) for file_name in file_names]


def run(command: str) -> str:
    print(f"about to run the command `{command}`")
    completed_process = subprocess.run(
        f"set -euo pipefail && ({command})",
        shell=True,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        executable="/bin/bash",
    )
    assert [completed_process.returncode, completed_process.stderr] == [0, ""]
    return completed_process.stdout


class TestTrace:
    class TestIntegration:
        @staticmethod
        @pytest.fixture(autouse=True)
        def clean_up(
            test_directory_path: pathlib.Path,  # pylint: disable=redefined-outer-name
        ) -> typing.Generator[None, None, None]:
            shutil.rmtree(test_directory_path / "actual_output")
            shutil.rmtree(test_directory_path / "workDir")
            yield

        @staticmethod
        def test_simple(
            test_directory_path: pathlib.Path,  # pylint: disable=redefined-outer-name
        ) -> None:
            run(f"python3 ./glare/trace.py {test_directory_path}/config.ini -c 5 -ab 0")
            assert_equality_of_actual_and_expected_output(
                test_directory_path,
                [
                    "fDGPe_0.out",
                    "dgp_0.out",
                    "time.out",
                ],
            )
