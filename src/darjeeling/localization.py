# -*- coding: utf-8 -*-
__all__ = (
    'Metric',
    'Localization',
    'genprog',
    'ochiai',
    'ample',
    'tarantula',
    'jaccard'
)

from typing import (Dict, Callable, List, Iterator, FrozenSet, Sequence, Any,
                    Iterable, Optional, Mapping, Set)
import math
import json
import random
import bisect
import logging
import functools

from .problem import Problem
from .core import FileLine, FileLineMap, FileLineSet, TestCoverageMap
from .spectra import Spectra
from .exceptions import NoImplicatedLines, BadConfigurationException
from .config import LocalizationConfig

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

Metric = Callable[[int, int, int, int], float]


def genprog(ep: int, np: int, ef: int, nf: int) -> float:
    if ef == 0:
        return 0.0
    if ep == 0:
        return 1.0
    return 0.1


def ochiai(ep: int, np: int, ef: int, nf: int) -> float:
    return ef / math.sqrt((ef + ep) * (ef + nf))


def ample(ep: int, np: int, ef: int, nf: int) -> float:
    return abs((ef / (ef + nf)) - (ep / (ep + np)))


def jaccard(ep: int, np: int, ef: int, nf: int) -> float:
    return ef / (ef + nf + ep)


def tarantula(ep: int, np: int, ef: int, nf: int) -> float:
    top = ef / (ef + nf)
    br = ep / (ep + np)
    bottom = top + br
    return top / bottom


class Localization:
    @staticmethod
    def from_coverage(coverage: TestCoverageMap,
                      metric: Metric
                      ) -> 'Localization':
        spectra = Spectra.from_coverage(coverage)
        return Localization.from_spectra(spectra, metric)

    @staticmethod
    def from_spectra(spectra: Spectra, metric: Metric) -> 'Localization':
        scores: FileLineMap[float] = FileLineMap({})
        for line in spectra:
            row = spectra[line]
            scores[line] = metric(row.ep, row.np, row.ef, row.nf)
        return Localization(scores)

    @staticmethod
    def from_config(coverage: TestCoverageMap,
                    cfg: LocalizationConfig
                    ) -> 'Localization':
        # find the suspiciousness metric
        try:
            supported_metrics = {
                'genprog': genprog,
                'tarantula': tarantula,
                'ochiai': ochiai,
                'jaccard': jaccard,
                'ample': ample
            }
            logger.info("supported suspiciousness metrics: %s",
                        ', '.join(supported_metrics.keys()))
            metric = supported_metrics[cfg.metric]
        except KeyError:
            m = "suspiciousness metric not supported: {}"
            m = m.format(cfg.metric)
            raise BadConfigurationException(m)
        logger.info("using suspiciousness metric: %s", cfg.metric)

        loc = Localization.from_coverage(coverage, metric)
        loc = loc.exclude_files(cfg.exclude_files)
        loc = loc.exclude_lines(cfg.exclude_lines)
        if cfg.restrict_to_files:
            loc = loc.restrict_to_files(cfg.restrict_to_files)
        if cfg.restrict_to_lines:
            loc = loc.restrict_to_lines(cfg.restrict_to_lines)
        return loc

    @staticmethod
    def from_dict(d: Dict[str, float]) -> 'Localization':
        scores = {FileLine.from_string(l): v for (l, v) in d.items()}
        return Localization(scores)

    @staticmethod
    def from_file(fn: str) -> 'Localization':
        logger.debug("loading localization from file: %s", fn)
        with open(fn, 'r') as f:
            jsn = json.load(f)
        localization = Localization.from_dict(jsn)
        logger.debug("loaded localization from file: %s", fn)
        return localization

    def __init__(self, scores: Mapping[FileLine, float]) -> None:
        """
        Raises:
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
        self._files: Set[str] = set(line.filename for line in self._lines)

        num_implicated: int = len(self.__line_to_score)
        if num_implicated == 0:
            raise NoImplicatedLines

        # FIXME use np.array
        # compute cumulative distribution function
        sm = sum(self.__line_to_score.values())
        pdf: List[float] = [s / sm for s in self.__line_to_score.values()]
        self.__cdf: List[float] = [0.0] + pdf[:-1]
        cum = 0.0
        for i in range(1, num_implicated):
            cum = self.__cdf[i] + cum
            self.__cdf[i] = cum

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Localization):
            return False
        lines_self: Set[FileLine] = set(self._lines)
        lines_other: Set[FileLine] = set(other._lines)
        if lines_self != lines_other:
            return False
        return all(self[l] == other[l] for l in lines_self)

    def to_dict(self) -> Dict[str, float]:
        """
        Transforms this fault localization to a dictionary, ready to be
        serialized into JSON or YAML.
        """
        return {str(line): val
                for (line, val) in self.__line_to_score.items()
                if val > 0.0}

    def to_file(self, fn: str) -> None:
        """Dumps this fault localization to a given file."""
        logger.debug("writing localization to file: %s", fn)
        jsn = self.to_dict()
        with open(fn, 'w') as f:
            json.dump(jsn, f)
        logger.debug("wrote localization to file: %s", fn)

    def __iter__(self) -> Iterator[FileLine]:
        """
        Returns an iterator over the suspicious lines contained within this
        fault localization.
        """
        yield from self.__line_to_score

    def __getitem__(self, line: FileLine) -> float:
        """
        Returns the suspiciousness score for a given line. If the line is not
        contained within the fault localization, a score of zero will be
        returned.
        """
        return self.__line_to_score.get(line, 0.0)

    def __contains__(self, line: FileLine) -> bool:
        """
        Determines whether a given line is deemed suspicious by this fault
        localization.
        """
        return line in self.__line_to_score

    def exclude_files(self,
                      files_to_exclude: Iterable[str]
                      ) -> 'Localization':
        """
        Returns a variant of this fault localization that does not contain
        lines from any of the specified files.
        """
        lines = [l for l in self if l.filename not in files_to_exclude]
        return self.restrict_to_lines(lines)

    def exclude_lines(self, lines: Iterable[FileLine]) -> 'Localization':
        """
        Returns a variant of this fault localization that does not contain any
        of the specified lines.

        Raises:
            NoImplicatedLines: if no lines are determined to be suspicious
                within the resulting localization.
        """
        scores = {l: s for (l, s) in self.__line_to_score.items()
                  if l not in lines}
        return Localization(scores)

    def without(self, line: FileLine) -> 'Localization':
        """
        Returns a variant of this fault localization that does not contain a
        given line.
        """
        scores = self.__line_to_score.copy()
        if line in scores:
            del scores[line]
        return Localization(scores)

    def restrict_to_files(self,
                          restricted_files: Iterable[str]
                          ) -> 'Localization':
        """
        Returns a variant of this fault localization that is restricted to
        lines that belong to a given set of files.
        """
        lines = [l for l in self if l.filename in restricted_files]
        return self.restrict_to_lines(lines)

    def restrict_to_lines(self,
                          lines: Iterable[FileLine]
                          ) -> 'Localization':
        """
        Returns a variant of this fault localization that is restricted to a
        given set of lines.

        Raises:
            NoImplicatedLines: if no lines are determined to be suspicious
                within the resulting localization.
        """
        scores = {l: s for (l, s) in self.__line_to_score.items()
                  if l in lines}
        return Localization(scores)

    def sample(self) -> FileLine:
        """
        Samples a line from this fault localization according to the implicit
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
    def files(self) -> List[str]:
        """A list of files that contain suspicious lines."""
        return list(self._files)

    def __repr__(self) -> str:
        # FIXME order!
        repr_scores = ["  {}: {:.2f}".format(str(l), self[l])
                       for l in sorted(self._lines)]
        return 'Localization(\n{})'.format(';\n'.join(repr_scores))
