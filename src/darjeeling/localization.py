__all__ = ['Metric', 'Localization']

from typing import Dict, Callable, List, Iterator, FrozenSet, Sequence
import random
import bisect
import logging

from bugzoo.core.spectra import Spectra
from bugzoo.core.coverage import TestSuiteCoverage

from .problem import Problem
from .core import FileLine
from .exceptions import NoImplicatedLines

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

Metric = Callable[[int, int, int, int], float]


class Localization(object):
    @staticmethod
    def from_problem(problem: Problem,
                     metric: Metric
                     ) -> 'Localization':
        return Localization.from_coverage(problem.coverage, metric)

    @staticmethod
    def from_coverage(coverage: TestSuiteCoverage,
                      metric: Metric
                      ) -> 'Localization':
        spectra = Spectra.from_coverage(coverage)
        return Localization.from_spectra(spectra, metric)

    @staticmethod
    def from_spectra(spectra: Spectra,
                     metric: Metric
                     ) -> 'Localization':
        scores = {}  # type: Dict[FileLine, float]
        for line in spectra:
            row = spectra[line]
            scores[line] = metric(row.ep, row.np, row.ef, row.nf)
        return Localization(scores)

    def __init__(self, scores: Dict[FileLine, float]) -> None:
        """
        Raises:
            NoImplicatedLines: if no lines are determined to be suspicious.
            ValueError: if a line is assigned a negative suspiciousness.
        """
        assert scores != []
        self.__line_to_score = scores.copy()
        self.__lines = []  # type: List[FileLine]
        self.__scores = []  # type: List[float]
        for line, score in scores.items():
            if score < 0.0:
                raise ValueError("suspiciousness values must be non-negative.")
            if score == 0.0:
                continue
            self.__lines.append(line)
            self.__scores.append(score)
        self.__files = \
            frozenset(line.filename for line in self.__lines)  # type: FrozenSet[str]  # noqa: pycodestyle

        if not self.__lines:
            raise NoImplicatedLines

        # compute cumulative distribution function
        sm = sum(self.__scores)
        pdf = [s / sm for s in self.__scores]
        self.__cdf = [0.0]  # type: List[float]
        cum = pdf[0]
        for p in pdf[1:]:
            self.__cdf.append(cum)
            cum += p

    def __iter__(self) -> Iterator[FileLine]:
        yield from self.__lines

    def __getitem__(self, line: FileLine) -> float:
        return self.__line_to_score.get(line, 0.0)

    def __contains__(self, line: FileLine) -> bool:
        """
        Determines whether a given line is deemed suspicious by this fault
        localization.
        """
        return line in self.__line_to_score

    def without(self, line: FileLine) -> 'Localization':
        scores = self.__line_to_score.copy()
        del scores[line]
        return Localization(scores)

    def restricted_to_lines(self, lines: Sequence[FileLine]) -> 'Localization':
        scores = {l: s for (l, s) in self.__line_to_score.items()
                  if l in lines}
        return Localization(scores)

    def sample(self) -> FileLine:
        mu = random.random()
        i = max(bisect.bisect_left(self.__cdf, mu) - 1, 0)
        assert i >= 0
        assert i < len(self.__cdf)
        return self.__lines[i]

    def __len__(self) -> int:
        """
        Returns a count of the number of suspicious lines.
        """
        return len(self.__lines)

    @property
    def files(self) -> List[str]:
        """
        Returns a list of files that contain suspicious lines.
        """
        return list(self.__files)

    def __repr__(self) -> str:
        # FIXME order!
        repr_scores = ["  {}: {:.2f}".format(str(l), self[l])
                       for l in sorted(self.__lines)]
        return 'Localization(\n{})'.format(';\n'.join(repr_scores))
