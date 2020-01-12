# -*- coding: utf-8 -*-
__all__ = ('Config', 'OptimizationsConfig', 'SchemaConfig',
           'CoverageConfig',
           'TransformationsConfig', 'LocalizationConfig')

from typing import (Optional, Collection, Tuple, Dict, Any, List, Set,
                    FrozenSet, Iterator, Type, NoReturn, Mapping)
import abc
import datetime
import sys
import typing
import random
import datetime
import logging
import os

import attr
import bugzoo

from .core import Language, FileLine, FileLineSet
from .util import dynamically_registered
from .exceptions import BadConfigurationException, LanguageNotSupported
from .test.config import TestSuiteConfig
from .searcher.config import SearcherConfig
from .coverage.config import CoverageConfig
from .transformation.config import TransformationSchemaConfig
from .program import ProgramDescriptionConfig

if typing.TYPE_CHECKING:
    from .environment import Environment
    from .problem import Problem
    from .test import TestSuite
    from .transformation import Transformation

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@attr.s(frozen=True)
class LocalizationConfig:
    metric: str = attr.ib()  # FIXME validate
    exclude_files: Collection[str] = attr.ib(factory=frozenset)
    exclude_lines: Collection[FileLine] = attr.ib(factory=frozenset)
    restrict_to_files: Optional[Collection[str]] = attr.ib(default=None)
    restrict_to_lines: Optional[Collection[FileLine]] = attr.ib(default=None)

    @restrict_to_files.validator
    def validate_restrict_to_files(self, attribute, value):
        if value is not None and not value:
            m = "cannot restrict to empty set of files"
            raise BadConfigurationException(m)

    @restrict_to_files.validator
    def validate_restrict_to_lines(self, attribute, value):
        if value is not None and not value:
            m = "cannot restrict to empty set of lines"
            raise BadConfigurationException(m)

    @staticmethod
    def from_yml(yml) -> 'LocalizationConfig':
        if not isinstance(yml, dict):
            m = "'localization' section should be an object"
            raise BadConfigurationException(m)
        if not 'metric' in yml:
            m = "'metric' property is missing from 'localization' section"
            raise BadConfigurationException(m)
        if not isinstance(yml['metric'], str):
            m = "'metric' property in 'localization' should be a string"
            raise BadConfigurationException(m)

        metric: str = yml['metric']
        exclude_files: Collection[str] = yml.get('exclude-files', [])
        restrict_to_files = yml.get('restrict-to-files')

        exclude_lines_arg: Dict[str, List[int]] = yml.get('exclude-lines', {})
        exclude_lines: Set[FileLine] = set()
        for fn in exclude_lines_arg:
            for line_num in exclude_lines_arg[fn]:
                exclude_lines.add(FileLine(fn, line_num))

        restrict_lines_arg = yml.get('restrict-to-lines')
        restrict_to_lines: Optional[Set[FileLine]] = None
        if restrict_lines_arg is not None:
            restrict_to_lines = set()
            assert restrict_to_lines is not None  # mypy is stupid
            for fn in restrict_lines_arg:
                for line_num in restrict_lines_arg[fn]:
                    restrict_to_lines.add(FileLine(fn, line_num))
            restrict_to_lines = FileLineSet.from_iter(restrict_to_lines)

        return LocalizationConfig(metric=metric,
                                  exclude_files=exclude_files,
                                  exclude_lines=exclude_lines,
                                  restrict_to_files=restrict_to_files,
                                  restrict_to_lines=restrict_to_lines)


@attr.s(frozen=True)
class OptimizationsConfig:
    """Specifies which optimizations should be applied during search."""
    use_scope_checking: bool = attr.ib(default=False)
    use_syntax_scope_checking: bool = attr.ib(default=True)
    ignore_dead_code: bool = attr.ib(default=False)
    ignore_equivalent_appends: bool = attr.ib(default=False)
    ignore_untyped_returns: bool = attr.ib(default=False)
    ignore_string_equivalent_snippets: bool = attr.ib(default=False)
    ignore_decls: bool = attr.ib(default=True)
    only_insert_executed_code = attr.ib(default=False)

    @staticmethod
    def from_yml(yml) -> 'OptimizationsConfig':
        return OptimizationsConfig(
            use_scope_checking=yml.get('use-scope-checking', True),
            use_syntax_scope_checking=yml.get('use-syntax-scope-checking', True),
            ignore_dead_code=yml.get('ignore-dead-code', True),
            ignore_equivalent_appends=yml.get('ignore-equivalent-prepends', True),
            ignore_untyped_returns=yml.get('ignore-untyped-returns', True),
            ignore_string_equivalent_snippets=yml.get('ignore-string-equivalent-snippets', True),
            ignore_decls=yml.get('ignore-decls', True),
            only_insert_executed_code=yml.get('only-insert-executed-code', True))


@attr.s(frozen=True)
class TransformationsConfig:
    """Specifies which transformations should be applied by the search."""
    schemas: Collection[TransformationSchemaConfig] = attr.ib(default=tuple())

    @classmethod
    def from_dict(cls,
                  dict_: Mapping[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'TransformationsConfig':
        if not 'schemas' in dict_:
            m = "'schemas' property missing in 'transformations' section"
            raise BadConfigurationException(m)
        if not isinstance(dict_['schemas'], list):
            m = "'schemas' property should be a list"
            raise BadConfigurationException(m)

        schemas: Collection[TransformationSchemaConfig] = \
            tuple(TransformationSchemaConfig.from_dict(dict_inner, dir_)
                  for dict_inner in dict_['schemas'])
        return TransformationsConfig(schemas)


@attr.s(frozen=True, auto_attribs=True)
class Config:
    """A configuration for Darjeeling.

    Attributes
    ----------
    dir_patches: str
        The absolute path to the directory to which patches should be saved.
    seed: int
        The seed that should be used by the random number generator.
    terminate_early: bool
        Specifies whether or not the search should terminate upon
        discovering an acceptable patch.
    threads: int
        The number of threads over which the search should be distributed.
    limit_candidates: int, optional
        An optional limit on the number of candidate patches that may be
        considered by the search.
    limit_time_minutes: int, optional
        An optional limit on the number of minutes that may be spent
        searching for an acceptable patch.
    search: SearcherConfig
        The configuration used by the search algorithm.
    program: ProgramDescriptionConfig
        A description of the program under transformation.
    """
    dir_patches: str = attr.ib()
    program: ProgramDescriptionConfig
    transformations: TransformationsConfig
    localization: LocalizationConfig
    search: SearcherConfig
    coverage: CoverageConfig
    seed: int = attr.ib(default=0)
    optimizations: OptimizationsConfig = attr.ib(factory=OptimizationsConfig)
    terminate_early: bool = attr.ib(default=True)
    threads: int = attr.ib(default=1)
    limit_candidates: Optional[int] = attr.ib(default=None)
    limit_time_minutes: Optional[float] = attr.ib(default=None)

    @seed.validator
    def validate_seed(self, attribute, value):
        if value < 0:
            m = "'seed' should be greater than or equal to zero."
            raise BadConfigurationException(m)

    @dir_patches.validator
    def validate_patches(self, attribute, value):
        if not os.path.isabs(value):
            m = "patch directory should be an absolute path."
            raise BadConfigurationException(m)

    @threads.validator
    def validate_threads(self, attribute, value):
        if value < 1:
            m = "number of threads must be greater than or equal to 1."
            raise BadConfigurationException(m)

    @limit_time_minutes.validator
    def validate_limit_time_minutes(self, attribute, value):
        if value is not None and value < 1:
            m = "time limit must be greater than or equal to one minute"
            raise BadConfigurationException(m)

    @property
    def limit_time(self) -> Optional[datetime.timedelta]:
        if self.limit_time_minutes:
            return datetime.timedelta(minutes=self.limit_time_minutes)
        return None

    @staticmethod
    def from_yml(yml: Dict[str, Any],
                 dir_: Optional[str] = None,
                 *,
                 terminate_early: bool = True,
                 seed: Optional[int] = None,
                 threads: Optional[int] = None,
                 limit_candidates: Optional[int] = None,
                 limit_time_minutes: Optional[int] = None,
                 dir_patches: Optional[str] = None
                 ) -> 'Config':
        """Loads a configuration from a YAML dictionary.

        Raises
        ------
        BadConfigurationException
            If an illegal configuration is provided.
        """
        def err(m: str) -> NoReturn:
            raise BadConfigurationException(m)

        has_limits = 'resource-limits' in yml

        if dir_patches is None and 'save-patches-to' in yml:
            dir_patches = yml['save-patches-to']
            if not isinstance(dir_patches, str):
                err("'save-patches-to' property should be a string")
            if not os.path.isabs(dir_patches):
                if not dir_:
                    err("'save-patches-to' must be absolute for non-file-based configurations")
                dir_patches = os.path.join(dir_, dir_patches)
        elif dir_patches is None:
            if not dir_:
                err("'save-patches-to' must be specified for non-file-based configurations")
            dir_patches = os.path.join(dir_, 'patches')

        if threads is None and 'threads' in yml:
            if not isinstance(yml['threads'], int):
                err("'threads' property should be an int")
            threads = yml['threads']
        elif threads is None:
            threads = 1

        # no seed override; seed provided in config
        if seed is None and 'seed' in yml:
            if not isinstance(yml['seed'], int):
                err("'seed' property should be an int.")
            seed = yml['seed']
        # no seed override or provided in config; use current date/time
        elif seed is None:
            random.seed(datetime.datetime.now())
            seed = random.randint(0, sys.maxsize)

        has_candidate_override = limit_candidates is not None
        has_candidate_limit = \
            has_limits and 'candidates' in yml['resource-limits']
        if not has_candidate_override and has_candidate_limit:
            if not isinstance(yml['resource-limits']['candidates'], int):
                err("'candidates' property in 'resource-limits' section should be an int")
            limit_candidates = yml['resource-limits']['candidates']

        has_time_override = limit_time_minutes is not None
        has_time_limit = \
            has_limits and 'time-minutes' in yml['resource-limits']
        if not has_time_override and has_time_limit:
            if not isinstance(yml['resource-limits']['time-minutes'], int):
                err("'time-minutes' property in 'resource-limits' section should be an int")  # noqa: pycodestyle
            limit_time_minutes = yml['resource-limits']['time-minutes']

        opts = OptimizationsConfig.from_yml(yml.get('optimizations', {}))

        # coverage config
        if 'coverage' in yml:
            coverage = CoverageConfig.from_dict(yml['coverage'], dir_)
        else:
            m = "'coverage' section is expected"
            raise BadConfigurationException(m)

        # fetch the transformation schemas
        if 'transformations' not in yml:
            err("'transformations' section is missing")
        if not isinstance(yml['transformations'], dict):
            err("'transformations' section should be an object")
        transformations = \
            TransformationsConfig.from_dict(yml['transformations'], dir_)

        if 'localization' not in yml:
            err("'localization' section is missing")
        localization = LocalizationConfig.from_yml(yml['localization'])

        if 'algorithm' not in yml:
            err("'algorithm' section is missing")
        search = SearcherConfig.from_dict(yml['algorithm'], dir_)

        if 'program' not in yml:
            err("'program' section is missing")
        program = ProgramDescriptionConfig.from_dict(yml['program'], dir_)

        return Config(seed=seed,
                      threads=threads,
                      terminate_early=terminate_early,
                      limit_time_minutes=limit_time_minutes,
                      limit_candidates=limit_candidates,
                      transformations=transformations,
                      program=program,
                      localization=localization,
                      coverage=coverage,
                      search=search,
                      optimizations=opts,
                      dir_patches=dir_patches)
