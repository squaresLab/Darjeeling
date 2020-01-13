# -*- coding: utf-8 -*-
"""
This module is responsible for describing concrete transformations to source
code files.
"""
from typing import (List, Iterator, Dict, FrozenSet, Tuple, Iterable, Type,
                    Optional, Any, Mapping)
import os
import random
import typing

from kaskara import InsertionPoint
from loguru import logger
import attr

from .base import Transformation, TransformationSchema
from .config import TransformationSchemaConfig
from .classic import *
from .line import *
from ..exceptions import NoImplicatedLines
from ..localization import Localization
from ..snippet import Snippet, SnippetDatabase
from ..core import Replacement, FileLine, FileLocationRange, FileLocation, \
                   FileLineSet, Location, LocationRange

if typing.TYPE_CHECKING:
    from ..problem import Problem


def find_all(problem: 'Problem',
             lines: List[FileLine],
             snippets: SnippetDatabase,
             schemas: List[TransformationSchema]
             ) -> Iterator[Transformation]:
    """
    Returns an iterator over the set of all transformations that can be
    performed at a given set of lines using provided schemas and snippets.
    """
    for schema in schemas:
        line_to_trans = schema.all_at_lines(lines)
        for line in lines:
            yield from line_to_trans[line]


def sample_by_localization_and_type(problem: 'Problem',
                                    snippets: SnippetDatabase,
                                    localization: Localization,
                                    schemas: List[TransformationSchema],
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
    lines: List[FileLine] = list(localization)
    try:
        schema_to_transformations_by_line = {
            s: s.all_at_lines(lines)
            for s in schemas
        }  # type: Dict[TransformationSchema, Mapping[FileLine, Iterator[Transformation]]]  # noqa: pycodestyle
        logger.debug("built schema->line->transformations map")
    except Exception:
        logger.exception("failed to build schema->line->transformations map")
        raise

    try:
        line_to_transformations_by_schema = {
            line: {sc: schema_to_transformations_by_line[sc].get(line, iter([])) for sc in schemas}  # noqa: pycodestyle
            for line in lines
        } # type: Dict[FileLine, Dict[TransformationSchema, Iterator[Transformation]]]  # noqa: pycodestyle
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
        }  # type: Dict[FileLine, Dict[TransformationSchema, List[Transformation]]]
        logger.info('finished eagerly computing entire transformation space')

        # compute stats
        num_transformations_by_line: Dict[FileLine, int] = {
            line: 0 for line in lines}
        num_transformations_by_schema: Dict[TransformationSchema, int] = {
            schema: 0 for schema in schemas}
        num_transformations_by_file: Dict[str, int] = {}

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
        logger.info(f"# transformations: {num_transformations_total}")
        logger.debug("# transformations by file:\n{}",
                     "\n".join([f'  * {fn}: {num}'
                                for (fn, num) in num_transformations_by_file.items()]))  # noqa: pycodestyle
        logger.debug("# transformations by schema:\n{}",
                     "\n".join([f'  * {sc}: {num}'
                                for (sc, num) in num_transformations_by_schema.items()]))  # noqa
        logger.debug("# transformations by line:\n{}",
                     "\n".join(['  * {str(line)}: {num}'
                                for (line, num) in num_transformations_by_line.items()]))  # noqa

        # TODO apply optional randomization

        logger.info('constructing transformation stream from precomputed transformations')  # noqa
        line_to_transformations_by_schema = {
            line: {schema: iter(collect_transformations[line][schema])
                   for schema in schemas}
            for line in lines
        }
        logger.info('constructed transformation stream from precomputed transformations')  # noqa

    def sample(localization: Localization) -> Iterator[Transformation]:
        while True:
            line = localization.sample()
            logger.debug(f"finding transformation at line: {line}")
            transformations_by_schema = line_to_transformations_by_schema[line]

            if not transformations_by_schema:
                logger.debug(f"no transformations left at {line}")
                del line_to_transformations_by_schema[line]
                try:
                    localization = localization.without(line)
                except NoImplicatedLines:
                    logger.debug("no transformations left in search space")
                    return
                continue

            schema = random.choice(list(transformations_by_schema.keys()))
            transformations = transformations_by_schema[schema]
            logger.debug(f"generating transformation using {schema} at {line}")

            # attempt to fetch the next transformation for the line and schema
            # if none are left, we remove the schema choice
            try:
                t = next(transformations)
                logger.debug(f"sampled transformation: {t}")
                yield t
            except StopIteration:
                logger.debug(f"no {schema} left at {line}")
                try:
                    del transformations_by_schema[schema]
                    logger.debug(f"removed entry for schema {schema} at line {line}")  # noqa
                except Exception:
                    logger.exception(
                        "failed to remove entry for {} at {}.\nchoices: {}",
                        schema, line, list(transformations_by_schema.keys()))
                    raise

    yield from sample(localization)
