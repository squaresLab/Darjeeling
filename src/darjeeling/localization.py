from __future__ import annotations

__all__ = (
    "SuspiciousnessMetric",
    "Localization",
    "genprog",
    "ochiai",
    "ample",
    "tarantula",
    "jaccard",
)

import bisect
import functools
import json
import math
import random
import typing
from collections.abc import Callable, Iterable, Iterator, Mapping, MutableMapping, Sequence

from loguru import logger

from .core import FileLine, FileLineMap, TestCoverageMap
from .exceptions import BadConfigurationException, NoImplicatedLines
from .spectra import Spectra

if typing.TYPE_CHECKING:
    from .config import LocalizationConfig

SuspiciousnessMetric = Callable[
    [Spectra],
    MutableMapping[FileLine, float],
]


def absolute_suspiciousness_metric(
    f: Callable[[int, int, int, int], float],
) -> SuspiciousnessMetric:
    @functools.wraps(f)
    def wrapper(spectra: Spectra) -> MutableMapping[FileLine, float]:
        line_to_score: FileLineMap[float] = FileLineMap({})
        for line in spectra:
            row = spectra[line]
            score = f(row.ep, row.np, row.ef, row.nf)
            line_to_score[line] = score
        return line_to_score

    return wrapper


@absolute_suspiciousness_metric
def genprog(ep: int, np: int, ef: int, nf: int) -> float:
    if ef == 0:
        return 0.0
    if ep == 0:
        return 1.0
    return 0.1


def weighted(spectra: Spectra) -> MutableMapping[FileLine, float]:
    num_lines_executed_by_only_failing_tests = 0
    num_lines_executed_by_both_passing_and_failing_tests = 0
    for line in spectra:
        row = spectra[line]
        if row.ef == 0:
            continue
        if row.ep == 0:
            num_lines_executed_by_only_failing_tests += 1
        else:
            num_lines_executed_by_both_passing_and_failing_tests += 1

    score_executed_by_only_failing_tests = \
        1.0 / num_lines_executed_by_only_failing_tests
    score_executed_by_both_passing_and_failing_tests = \
        0.1 / num_lines_executed_by_both_passing_and_failing_tests

    line_to_score: FileLineMap[float] = FileLineMap({})
    for line in spectra:
        row = spectra[line]
        if row.ef == 0:
            continue
        if row.ep == 0:
            score = score_executed_by_only_failing_tests
        else:
            score = score_executed_by_both_passing_and_failing_tests
        line_to_score[line] = score

    return line_to_score


@absolute_suspiciousness_metric
def ochiai(ep: int, np: int, ef: int, nf: int) -> float:
    return ef / math.sqrt((ef + ep) * (ef + nf))


@absolute_suspiciousness_metric
def ample(ep: int, np: int, ef: int, nf: int) -> float:
    return abs((ef / (ef + nf)) - (ep / (ep + np)))


@absolute_suspiciousness_metric
def jaccard(ep: int, np: int, ef: int, nf: int) -> float:
    return ef / (ef + nf + ep)


@absolute_suspiciousness_metric
def tarantula(ep: int, np: int, ef: int, nf: int) -> float:
    # protect against division by zero
    tests_at_line = ep + ef
    num_passing_tests = ep + np
    num_failing_tests = ef + nf

    if tests_at_line == 0:
        return 0

    top = ef / num_failing_tests
    br = ep / num_passing_tests if num_passing_tests > 0 else 0
    bottom = top + br
    return top / bottom


class Localization:
    @staticmethod
    def from_coverage(
        coverage: TestCoverageMap,
        metric: SuspiciousnessMetric,
    ) -> Localization:
        spectra = Spectra.from_coverage(coverage)
        return Localization.from_spectra(spectra, metric)

    @staticmethod
    def from_spectra(
        spectra: Spectra,
        metric: SuspiciousnessMetric,
    ) -> Localization:
        scores = metric(spectra)
        return Localization(scores)

    @staticmethod
    def from_config(
        coverage: TestCoverageMap,
        cfg: LocalizationConfig,
    ) -> Localization:
        # find the suspiciousness metric
        try:
            supported_metrics: Mapping[str, SuspiciousnessMetric] = {
                "genprog": genprog,
                "weighted": weighted,
                "tarantula": tarantula,
                "ochiai": ochiai,
                "jaccard": jaccard,
                "ample": ample,
            }
            logger.info("supported suspiciousness metrics: {}",
                        ", ".join(supported_metrics.keys()))
            metric: SuspiciousnessMetric = supported_metrics[cfg.metric]
        except KeyError:
            m = f"suspiciousness metric not supported: {cfg.metric}"
            raise BadConfigurationException(m)
        logger.info(f"using suspiciousness metric: {cfg.metric}")

        loc = Localization.from_coverage(coverage, metric)
        logger.trace(f"excluding files from localization: {cfg.exclude_files}")
        loc = loc.exclude_files(cfg.exclude_files)
        logger.trace(f"excluding lines from localization: {cfg.exclude_lines}")
        loc = loc.exclude_lines(cfg.exclude_lines)
        if cfg.restrict_to_files:
            loc = loc.restrict_to_files(cfg.restrict_to_files)
        if cfg.restrict_to_lines:
            loc = loc.restrict_to_lines(cfg.restrict_to_lines)
        return loc

    @staticmethod
    def from_dict(d: dict[str, float]) -> Localization:
        scores = {
            FileLine.from_string(l): v for (l, v) in d.items()
        }
        return Localization(scores)

    @staticmethod
    def from_file(fn: str) -> Localization:
        logger.debug(f"loading localization from file: {fn}")
        with open(fn) as f:
            jsn = json.load(f)
        localization = Localization.from_dict(jsn)
        logger.debug(f"loaded localization from file: {fn}")
        return localization

    def __init__(self, scores: Mapping[FileLine, float]) -> None:
        """Raises
        NoImplicatedLines: if no lines are determined to be suspicious.
        ValueError: if a line is assigned a negative suspiciousness.
        """
        self.__line_to_score: FileLineMap[float] = FileLineMap({})
        for line in sorted(scores):
            score = scores[line]
            if score < 0.0:
                raise ValueError("suspiciousness values must be non-negative.")
            if score == 0.0:
                continue
            self.__line_to_score[line] = score

        self._lines: Sequence[FileLine] = tuple(self.__line_to_score)
        self._files: set[str] = set(line.filename for line in self._lines)

        num_implicated: int = len(self.__line_to_score)
        if num_implicated == 0:
            raise NoImplicatedLines

        # FIXME use np.array
        # compute cumulative distribution function
        sm = sum(self.__line_to_score.values())
        pdf: list[float] = [s / sm for s in self.__line_to_score.values()]
        self.__cdf: list[float] = [0.0] + pdf[:-1]
        cum = 0.0
        for i in range(1, num_implicated):
            cum = self.__cdf[i] + cum
            self.__cdf[i] = cum

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Localization):
            return False
        lines_self: set[FileLine] = set(self._lines)
        lines_other: set[FileLine] = set(other._lines)
        if lines_self != lines_other:
            return False
        return all(self[line] == other[line] for line in lines_self)

    def to_dict(self) -> dict[str, float]:
        """Transforms this fault localization to a dictionary, ready to be
        serialized into JSON or YAML.
        """
        return {str(line): val
                for (line, val) in self.__line_to_score.items()
                if val > 0.0}

    def to_file(self, fn: str) -> None:
        """Dumps this fault localization to a given file."""
        logger.debug("writing localization to file: {fn}")
        jsn = self.to_dict()
        with open(fn, "w") as f:
            json.dump(jsn, f)
        logger.debug(f"wrote localization to file: {fn}")

    def __iter__(self) -> Iterator[FileLine]:
        """Returns an iterator over the suspicious lines contained within this
        fault localization.
        """
        yield from self.__line_to_score

    def __getitem__(self, line: FileLine) -> float:
        """Returns the suspiciousness score for a given line. If the line is not
        contained within the fault localization, a score of zero will be
        returned.
        """
        return self.__line_to_score.get(line, 0.0)

    def __contains__(self, line: FileLine) -> bool:
        """Determines whether a given line is deemed suspicious by this fault
        localization.
        """
        return line in self.__line_to_score

    def exclude_files(self,
                      files_to_exclude: Iterable[str],
                      ) -> Localization:
        """Returns a variant of this fault localization that does not contain
        lines from any of the specified files.
        """
        lines = [line for line in self if line.filename not in files_to_exclude]
        return self.restrict_to_lines(lines)

    def exclude_lines(self, lines: Iterable[FileLine]) -> Localization:
        """Returns a variant of this fault localization that does not contain any
        of the specified lines.

        Raises
        ------
            NoImplicatedLines: if no lines are determined to be suspicious
                within the resulting localization.
        """
        scores = {
            line: s for (line, s) in self.__line_to_score.items()
            if line not in lines
        }
        return Localization(scores)

    def without(self, line: FileLine) -> Localization:
        """Returns a variant of this fault localization that does not contain a
        given line.
        """
        return self.exclude_lines([line])

    def restrict_to_files(
        self,
        restricted_files: Iterable[str],
    ) -> Localization:
        """Returns a variant of this fault localization that is restricted to
        lines that belong to a given set of files.
        """
        lines = [line for line in self if line.filename in restricted_files]
        return self.restrict_to_lines(lines)

    def restrict_to_lines(
        self,
        lines: Iterable[FileLine],
    ) -> Localization:
        """Returns a variant of this fault localization that is restricted to a
        given set of lines.

        Raises
        ------
            NoImplicatedLines: if no lines are determined to be suspicious
                within the resulting localization.
        """
        scores = {
            line: score for (line, score) in self.__line_to_score.items()
            if line in lines
        }
        return Localization(scores)

    def sample(self) -> FileLine:
        """Samples a line from this fault localization according to the implicit
        probability distribution given by the suspiciousness values of the
        lines contained within this fault localization.
        """
        mu = random.random()
        i = max(bisect.bisect_left(self.__cdf, mu) - 1, 0)
        assert i >= 0
        assert i < len(self.__cdf)
        return self._lines[i]

    def __len__(self) -> int:
        """Returns a count of the number of suspicious lines."""
        return len(self._lines)

    @property
    def files(self) -> list[str]:
        """A list of files that contain suspicious lines."""
        return list(self._files)

    def __repr__(self) -> str:
        # FIXME order!
        repr_scores = [
            f"  {line!s}: {self[line]:.2f}"
            for line in sorted(self._lines)
        ]
        return "Localization(\n{})".format(";\n".join(repr_scores))
