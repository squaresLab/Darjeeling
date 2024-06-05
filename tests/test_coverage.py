import pytest

from darjeeling.core import FileLine, FileLineSet, TestCoverage, TestOutcome


def ln(num: int) -> FileLine:
    return FileLine("file.c", num)


@pytest.fixture()
def coverage() -> TestCoverage:
    outcome = TestOutcome(successful=True,
                          time_taken=0.35)
    lines = FileLineSet.from_list([ln(1), ln(2), ln(3)])
    return TestCoverage(test="foo",
                        outcome=outcome,
                        lines=lines)


def test_length(coverage):
    assert len(coverage) == 3


def test_contains(coverage):
    assert ln(1) in coverage
    assert ln(999) not in coverage
