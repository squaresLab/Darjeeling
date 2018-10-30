"""
This module is responsible for describing concrete transformations to source
code files.
"""
from typing import List, Iterator, Dict, FrozenSet, Tuple, Iterable, Type, \
                   Optional, Any
import logging
import os
import random

import attr
import rooibos
from kaskara import InsertionPoint

from .base import Transformation, register
from .rooibos import *
from .classic import *
from .line import *
from ..exceptions import NoImplicatedLines
from ..localization import Localization
from ..problem import Problem
from ..snippet import Snippet, SnippetDatabase
from ..core import Replacement, FileLine, FileLocationRange, FileLocation, \
                   FileLineSet, Location, LocationRange

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


def find_all(problem: Problem,
             lines: List[FileLine],
             snippets: SnippetDatabase,
             schemas: List[Type[Transformation]]
             ) -> Iterator[Transformation]:
    """
    Returns an iterator over the set of all transformations that can be
    performed at a given set of lines using provided schemas and snippets.
    """
    for schema in schemas:
        line_to_trans = schema.all_at_lines(problem, snippets, lines)
        for trans in line_to_trans.values():
            yield from trans


def sample_by_localization_and_type(problem: Problem,
                                    snippets: SnippetDatabase,
                                    localization: Localization,
                                    schemas: List[Type[Transformation]],
                                    *,
                                    eager: bool = False,
                                    randomize: bool = False,
                                    threads: int = 1
                                    ) -> Iterator[Transformation]:
    """
    Returns an iterator that samples transformations at the different lines
    contained within the fault localization in accordance to the probability
    distribution defined by their suspiciousness scores.
    """
    lines = list(localization)  # type: List[FileLine]
    try:
        schema_to_transformations_by_line = {
            s: s.all_at_lines(problem, snippets, lines, threads=threads)
            for s in schemas
        }  # type: Dict[Type[Transformation], Dict[FileLine, Iterator[Transformation]]]  # noqa: pycodestyle
        logger.debug("built schema->line->transformations map")
    except Exception:
        logger.exception("failed to build schema->line->transformations map")
        raise

    try:
        line_to_transformations_by_schema = {
            line: {sc: schema_to_transformations_by_line[sc].get(line, iter([])) for sc in schemas}  # noqa: pycodestyle
            for line in lines
        } # type: Dict[FileLine, Dict[Type[Transformation], Iterator[Transformation]]]  # noqa: pycodestyle
        logger.debug("built line->schema->transformations map")
    except Exception:
        logger.exception("failed to build line->schema->transformations map")
        raise

    if eager:
        logger.info('eagerly computing entire transformation space')
        collect_transformations = {
            line: {sc: list(line_to_transformations_by_schema[line][sc])
                   for sc in schemas}
            for line in lines
        }  # type: Dict[FileLine, Dict[Type[Transformation], List[Transformation]]]
        logger.info('finished eagerly computing entire transformation space')

        # compute stats
        num_transformations_by_line = {
            line: 0 for line in lines
        }  # type: Dict[FileLine, int]
        num_transformations_by_schema = {
            schema: 0 for schema in schemas
        }  # type: Dict[Type[Transformation], int]
        num_transformations_by_file = {}  # type: Dict[str, int]

        for line in lines:
            sc_to_tx = collect_transformations[line]
            for (sc, tx) in sc_to_tx.items():
                num_transformations_by_line[line] += len(tx)
                num_transformations_by_schema[sc] += len(tx)

        num_transformations_by_line = {
            line: num
            for (line, num) in num_transformations_by_line.items() if num > 0
        }

        for (line, num_tx) in num_transformations_by_line.items():
            filename = line.filename
            if filename not in num_transformations_by_file:
                num_transformations_by_file[filename] = 0
            num_transformations_by_file[filename] += num_tx

        num_transformations_total = sum(num_transformations_by_line.values())

        # report stats
        logger.info("# transformations: %d",
                    num_transformations_total)
        logger.debug("# transformations by file:\n%s",
                     "\n".join(['  * {}: {}'.format(fn, num)
                                for (fn, num) in num_transformations_by_file.items()]))  # noqa: pycodestyle
        logger.debug("# transformations by schema:\n%s",
                     "\n".join(['  * {}: {}'.format(sc.__name__, num)
                                for (sc, num) in num_transformations_by_schema.items()]))  # noqa: pycodestyle
        logger.debug("# transformations by line:\n%s",
                     "\n".join(['  * {}: {}'.format(str(line), num)
                                for (line, num) in num_transformations_by_line.items()]))  # noqa: pycodestyle

        # TODO apply optional randomization

        logger.info('constructing transformation stream from precomputed transformations')  # noqa: pycodestyle
        line_to_transformations_by_schema = {
            line: {schema: iter(collect_transformations[line][schema])
                   for schema in schemas}
            for line in lines
        }
        logger.info('constructed transformation stream from precomputed transformations')  # noqa: pycodestyle

    def sample(localization: Localization) -> Iterator[Transformation]:
        while True:
            line = localization.sample()
            logger.debug("finding transformation at line: %s", line)
            transformations_by_schema = line_to_transformations_by_schema[line]

            if not transformations_by_schema:
                logger.debug("no transformations left at %s", line)
                del line_to_transformations_by_schema[line]
                try:
                    localization = localization.without(line)
                except NoImplicatedLines:
                    logger.debug("no transformations left in search space")
                    raise StopIteration
                continue

            schema = random.choice(list(transformations_by_schema.keys()))
            transformations = transformations_by_schema[schema]
            logger.debug("generating transformation using %s at %s",
                         schema.__name__, line)

            # attempt to fetch the next transformation for the line and schema
            # if none are left, we remove the schema choice
            try:
                t = next(transformations)
                logger.debug("sampled transformation: %s", t)
                yield t
            except StopIteration:
                logger.debug("no %s left at %s", schema.__name__, line)
                try:
                    del transformations_by_schema[schema]
                    logger.debug("removed entry for schema %s at line %s",
                             schema.__name__, line)
                except Exception:
                    logger.exception(
                        "failed to remove entry for %s at %s.\nchoices: %s",
                        schema.__name__, line,
                        [s.__name__ for s in transformations_by_schema.keys()])
                    raise

    yield from sample(localization)
