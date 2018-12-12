__all__ = [
    'Metric',
    'Localization',
    'genprog',
    'ochiai',
    'ample',
    'tarantula',
    'jaccard'
]

from typing import Dict, Callable, List, Iterator, FrozenSet, Sequence, Any, \
    Iterable, Optional
import math
import json
import random
import bisect
import logging
import functools

from bugzoo.core.spectra import Spectra
from bugzoo.core.coverage import TestSuiteCoverage

from .problem import Problem
from .core import FileLine
from .exceptions import NoImplicatedLines, BadConfigurationException

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

    @staticmethod
    def from_config(coverage: TestSuiteCoverage,
                    cfg: Dict[str, Any]
                    ) -> 'Localization':
        if not isinstance(cfg, dict):
            m = "'localization' section should be an object"
            raise BadConfigurationException(m)
        if not 'metric' in cfg:
            m = "'metric' property is missing from 'localization' section"
            raise BadConfigurationException(m)
        if not isinstance(cfg['metric'], str):
            m = "'metric' property in 'localization' should be a string"
            raise BadConfigurationException(m)

        name_metric = cfg['metric']  # type: str
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
            metric = supported_metrics[name_metric]
        except KeyError:
            m = "suspiciousness metric not supported: {}".format(name_metric)
            raise BadConfigurationException(m)
        logger.info("using suspiciousness metric: %s", name_metric)

        # build base localization using given metric
        loc = Localization.from_coverage(coverage, metric)

        # exclude specified files
        exclude_files = cfg.get('exclude-files', [])  # type: List[str]
        loc = loc.exclude_files(exclude_files)

        # exclude specified lines
        exclude_lines_arg = \
            cfg.get('exclude-lines', {})  # type: Dict[str, List[int]]
        exclude_lines = []  # type: List[FileLine]
        for fn in exclude_lines_arg:
            for line_num in exclude_lines_arg[fn]:
                exclude_lines.append(FileLine(fn, line_num))
        loc = loc.exclude_lines(exclude_lines)

        # restrict to specified files
        restrict_to_files = cfg.get('restrict-to-files',
                                    None)  # type: Optional[List[str]]
        if restrict_to_files is []:
            m = "cannot restrict to empty set of files"
            raise BadConfigurationException(m)
        if restrict_to_files is not None:
            loc = loc.restrict_to_files(restrict_to_files)

        # restrict to specified lines
        restrict_lines_arg = cfg.get('restrict-to-lines',
                                     None)  # type: Optional[Dict[str, List[int]]]
        if restrict_lines_arg is []:
            m = "cannot restrict to empty set of lines"
            raise BadConfigurationException(m)
        if restrict_lines_arg is not None:
            restrict_to_lines = []  # type: List[FileLine]
            for fn in restrict_lines_arg:
                for line_num in restrict_lines_arg[fn]:
                    restrict_to_lines.append(FileLine(fn, line_num))
            loc = loc.restricted_to_lines(restrict_to_lines)

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

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Localization):
            return False
        lines_self = set(self)
        lines_other = set(other)
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
        """
        Dumps this fault localization to a given file.
        """
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
        yield from self.__lines

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

    def exclude_files(self, files_to_exclude: List[str]) -> 'Localization':
        """
        Returns a variant of this fault localization that does not contain
        lines from any of the specified files.
        """
        lines = [l for l in self if l.filename not in files_to_exclude]
        return self.restricted_to_lines(lines)

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

    def restrict_to_files(self, restricted_files: List[str]) -> 'Localization':
        """
        Returns a variant of this fault localization that is restricted to
        lines that belong to a given set of files.
        """
        lines = [l for l in self if l.filename in restricted_files]
        return self.restricted_to_lines(lines)

    def restricted_to_lines(self,
                            lines: Sequence[FileLine]
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
