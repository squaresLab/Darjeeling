from __future__ import annotations

__all__ = (
    "FileLine",
    "FileLineMap",
    "FileLineSet",
    "FileLocation",
    "FileLocationRange",
    "Location",
    "LocationRange",
    "Replacement",
    "TestCoverage",
    "TestCoverageMap",
)

import abc
import fnmatch
import functools
import typing as t
from collections import OrderedDict
from collections.abc import Iterable, Iterator, Mapping, Sequence
from enum import Enum

import attr
import yaml
from bugzoo.core import TestCoverage as BugZooTestCoverage
from bugzoo.core import TestOutcome as BugZooTestOutcome
from bugzoo.core import TestSuiteCoverage as BugZooTestSuiteCoverage
from sourcelocation import (
    FileLine,
    FileLineMap,
    FileLineSet,
    FileLocation,
    FileLocationRange,
    Location,
    LocationRange,
)

from darjeeling.exceptions import LanguageNotSupported


@attr.s(frozen=True, str=False, auto_attribs=True)
class Replacement:
    """Describes the replacement of a contiguous body of text in a single source
    code file with a provided text.

    Attributes
    ----------
    location: FileLocationRange
        The contiguous range of text that should be replaced.
    text: str
        The source text that should be used as a replacement.
    """
    location: FileLocationRange
    text: str

    @staticmethod
    def from_dict(d: dict[str, str]) -> Replacement:
        location = FileLocationRange.from_string(d["location"])
        return Replacement(location, d["text"])

    @classmethod
    def resolve(
        cls,
        replacements: Sequence[Replacement],
    ) -> list[Replacement]:
        """Resolves all conflicts in a sequence of replacements."""
        file_to_reps: dict[str, list[Replacement]] = {}
        for rep in replacements:
            if rep.filename not in file_to_reps:
                file_to_reps[rep.filename] = []
            file_to_reps[rep.filename].append(rep)

        # resolve redundant replacements
        for fn in file_to_reps:
            reps = file_to_reps[fn]

            def cmp(x: Location, y: Location) -> int:
                return -1 if x < y else 0 if x == y else 0

            def compare(x: Replacement, y: Replacement) -> int:
                start_x, stop_x = x.location.start, x.location.stop
                start_y, stop_y = y.location.start, y.location.stop
                if start_x != start_y:
                    return cmp(start_x, start_y)
                # start_x == start_y
                return -cmp(stop_x, stop_y)

            reps.sort(key=functools.cmp_to_key(compare))

            filtered: list[Replacement] = [reps[0]]
            i, j = 0, 1
            while j < len(reps):
                x, y = reps[i], reps[j]
                if x.location.stop > y.location.start:
                    j += 1
                else:
                    i += 1
                    j += 1
                    filtered.append(y)
            filtered.reverse()
            file_to_reps[fn] = filtered

        # collapse into a flat sequence of transformations
        resolved: list[Replacement] = []
        for reps in file_to_reps.values():
            resolved += reps
        return resolved

    @property
    def filename(self) -> str:
        """The name of the file in which the replacement should be made."""
        return self.location.filename

    def to_dict(self) -> dict[str, str]:
        return {"location": str(self.location),
                "text": self.text}


class Language(Enum):
    @classmethod
    def find(cls, name: str) -> Language:
        try:
            return next(line for line in cls if line.value == name)
        except StopIteration:
            raise LanguageNotSupported(name)

    C = "c"
    CPP = "cpp"
    PYTHON = "python"
    TEXT = "text"


class Test:
    """An individual test case for the program under repair."""
    @property
    @abc.abstractmethod
    def name(self) -> str:
        """A unique name for the test case."""
        raise NotImplementedError


@attr.s(frozen=True, slots=True, auto_attribs=True)
class TestOutcome:
    """Records the outcome of a test execution."""
    successful: bool
    time_taken: float

    @staticmethod
    def from_bugzoo(outcome: BugZooTestOutcome) -> TestOutcome:
        return TestOutcome(successful=outcome.passed,
                           time_taken=outcome.duration)

    @staticmethod
    def from_dict(d: dict[str, t.Any]) -> TestOutcome:
        return TestOutcome(d["successful"], d["time-taken"])

    def to_dict(self) -> dict[str, t.Any]:
        return {"successful": self.successful,
                "time-taken": self.time_taken}


@attr.s(frozen=True, slots=True, auto_attribs=True)
class BuildOutcome:
    """Records the outcome of a build attempt."""
    successful: bool
    time_taken: float

    def to_dict(self) -> dict[str, t.Any]:
        return {"successful": self.successful,
                "time-taken": self.time_taken}


class TestOutcomeSet:
    """Records the outcome of different test executions for a single patch."""
    def __init__(
        self,
        outcomes: dict[str, TestOutcome] | None = None,
    ) -> None:
        if outcomes is None:
            outcomes = {}
        self.__outcomes: dict[str, TestOutcome] = outcomes

    def __iter__(self) -> Iterator[str]:
        return self.__outcomes.keys().__iter__()

    def __getitem__(self, test: str) -> TestOutcome:
        return self.__outcomes[test]

    def with_outcome(self, test: str, outcome: TestOutcome) -> TestOutcomeSet:
        outcomes = self.__outcomes.copy()
        outcomes[test] = outcome
        return TestOutcomeSet(outcomes)

    def merge(self, other: TestOutcomeSet) -> TestOutcomeSet:
        outcomes = self.__outcomes.copy()
        for test_name in other:
            outcomes[test_name] = other[test_name]
        return TestOutcomeSet(outcomes)

    def to_dict(self) -> list[dict[str, t.Any]]:
        return [outcome.to_dict() for outcome in self.__outcomes.values()]


@attr.s(frozen=True, slots=True, auto_attribs=True)
class TestCoverage:
    """Describes the lines that were executed during a given test execution."""
    test: str
    outcome: TestOutcome
    lines: FileLineSet

    @staticmethod
    def from_bugzoo(coverage: BugZooTestCoverage) -> TestCoverage:
        return TestCoverage(
            test=coverage.test,
            outcome=TestOutcome.from_bugzoo(coverage.outcome),
            lines=coverage.lines)

    @staticmethod
    def from_dict(d: dict[str, t.Any]) -> TestCoverage:
        name = d["name"]
        outcome = TestOutcome.from_dict(d["outcome"])
        lines = FileLineSet.from_dict(d["lines"])
        return TestCoverage(name, outcome, lines)

    def to_dict(self) -> dict[str, t.Any]:
        return {"name": self.test,
                "outcome": self.outcome.to_dict(),
                "lines": self.lines.to_dict()}

    def __contains__(self, elem: object) -> bool:
        return elem in self.lines

    def __iter__(self) -> Iterator[FileLine]:
        yield from self.lines

    def __len__(self) -> int:
        return len(self.lines)

    def restrict_to_files(self, files: Iterable[str]) -> TestCoverage:
        """Returns a variant of this coverage, restricted to given files.

        Parameters
        ----------
        files: Iterable[str]
            A list of filenames (that may or may not contain Unix wildcards)
        """
        lines: list[FileLine] = []
        # NOTE this could be _much_ more efficient, but for now, performance
        # isnt really a concern
        for line in self:
            filename = line.filename
            if any(True for pattern in files if fnmatch.fnmatch(filename, pattern)):
                lines.append(line)
        return TestCoverage(self.test, self.outcome, FileLineSet.from_iter(lines))

    def restrict_to_locations(self,
                              locations: Iterable[FileLine],
                              ) -> TestCoverage:
        """Returns a variant of this coverage, restricted to given locations.
        """
        lines = self.lines.intersection(locations)
        return TestCoverage(self.test, self.outcome, lines)


class TestCoverageMap(Mapping[str, TestCoverage]):
    """Contains coverage information for each test within a test suite."""
    @staticmethod
    def from_bugzoo(coverage: BugZooTestSuiteCoverage) -> TestCoverageMap:
        return TestCoverageMap({test_name: TestCoverage.from_bugzoo(test_cov)
                                for (test_name, test_cov) in coverage.items()})

    def __init__(self, mapping: Mapping[str, TestCoverage]):
        self.__mapping: OrderedDict[str, TestCoverage] = OrderedDict()
        for test_name in sorted(mapping):
            self.__mapping[test_name] = mapping[test_name]

    @classmethod
    def from_file(cls, fn: str) -> TestCoverageMap:
        with open(fn) as fh:
            dict_ = yaml.safe_load(fh)
        return cls.from_dict(dict_)

    def to_file(self, fn: str) -> None:
        dict_ = self.to_dict()
        with open(fn, "w") as fh:
            yaml.dump(dict_, fh, indent=2, default_flow_style=False)

    @classmethod
    def from_dict(cls, d: list[dict[str, t.Any]]) -> TestCoverageMap:
        name_to_coverage: dict[str, TestCoverage] = {}
        for d_test in d:
            name = d_test["name"]
            coverage = TestCoverage.from_dict(d_test)
            name_to_coverage[name] = coverage
        return TestCoverageMap(name_to_coverage)

    def to_dict(self) -> list[dict[str, t.Any]]:
        return [coverage.to_dict() for coverage in self.values()]

    def __len__(self) -> int:
        """Returns the number of tests represented in this map."""
        return len(self.__mapping)

    def __getitem__(self, name: str) -> TestCoverage:
        """Returns the coverage for a test given by its name."""
        return self.__mapping[name]

    def __iter__(self) -> Iterator[str]:
        """Returns an iterator over the names of the tests in this map."""
        yield from self.__mapping

    def __str__(self) -> str:
        out_lines: list[str] = []
        for name_test in self:
            coverage_test = self[name_test]
            result = "PASS" if coverage_test.outcome.successful else "FAIL"
            lines_covered = coverage_test.lines
            out_lines.append(f"{name_test} [{result}]: {{")
            out_lines.extend("  " + s for s in str(lines_covered).split("\n"))
            out_lines.append("}")
        out = "\n".join(f"  {line}" for line in out_lines)
        out = f"{{\n{out}\n}}"
        return out

    @property
    def passing(self) -> TestCoverageMap:
        """Returns a variant of this mapping restricted to passing tests."""
        contents = {name: coverage for (name, coverage)
                    in self.__mapping.items()
                    if coverage.outcome.successful}
        return TestCoverageMap(contents)

    @property
    def failing(self) -> TestCoverageMap:
        """Returns a variant of this mapping restricted to failing tests."""
        contents = {name: coverage for (name, coverage)
                    in self.__mapping.items()
                    if not coverage.outcome.successful}
        return TestCoverageMap(contents)

    @property
    def locations(self) -> t.AbstractSet[FileLine]:
        """Returns the set of all locations that are covered in this map."""
        locs = FileLineSet()
        if not self.__mapping:
            return locs
        return locs.union(*self.values())

    def covering_tests(self, location: FileLine) -> set[str]:
        """Returns the names of the tests that cover a given location."""
        return set(name for (name, cov) in self.__mapping.items()
                   if location in cov)

    def restrict_to_files(self, files: Iterable[str]) -> TestCoverageMap:
        """Returns a variant of this map that only contains coverage for a given
        set of files.
        """
        return TestCoverageMap({test: cov.restrict_to_files(files)
                                for (test, cov) in self.items()})

    def restrict_to_locations(self,
                              locations: Iterable[FileLine],
                              ) -> TestCoverageMap:
        """Returns a variant of this map with its coverage restricted to a given
        set of locations.
        """
        return TestCoverageMap({test: cov.restrict_to_locations(locations)
                                for (test, cov) in self.items()})
