# -*- coding: utf-8 -*-
__all__ = ('Config', 'OptimizationsConfig', 'SchemaConfig',
           'CoverageConfig',
           'SearcherConfig', 'TestSuiteConfig',
           'TransformationsConfig', 'LocalizationConfig')

from typing import (Optional, Collection, Tuple, Dict, Any, List, Set,
                    FrozenSet, Iterator, Type)
import abc
import sys
import random
import datetime
import logging
import os

import attr

from .core import Language, FileLine, FileLineSet
from .util import dynamically_registered
from .exceptions import BadConfigurationException, LanguageNotSupported

logger: logging.Logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dynamically_registered(lookup='lookup')
class SearcherConfig(abc.ABC):
    """Describes a search algorithm configuration."""
    @staticmethod
    def __iter__() -> Iterator[str]:
        ...

    @staticmethod
    def __len__() -> int:
        ...

    @staticmethod
    def lookup(name: str) -> Type['SearcherConfig']:
        ...

    @classmethod
    @abc.abstractmethod
    def from_dict(cls,
                  d: Dict[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'SearcherConfig':
        name_type: str = d['type']
        type_: Type[SearcherConfig] = SearcherConfig.lookup(name_type)
        return type_.from_dict(d, dir_)


@dynamically_registered(lookup='lookup', length=None, iterator=None)
class TestSuiteConfig(abc.ABC):
    """Describes a test suite configuration."""
    @staticmethod
    def lookup(name: str) -> Type['TestSuiteConfig']:
        ...

    @classmethod
    @abc.abstractmethod
    def from_dict(cls,
                  d: Dict[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'TestSuiteConfig':
        if 'type' not in d:
            logger.debug("using default BugZoo test suite")
            name_type = 'bugzoo'
        else:
            name_type = d['type']
        type_: Type[TestSuiteConfig] = TestSuiteConfig.lookup(name_type)
        return type_.from_dict(d, dir_)


@attr.s(frozen=True)
class CoverageConfig:
    """Holds instructions for collecting and processing coverage.

    Attributes
    ----------
    restrict_to_files: Set[str], optional
        An optional set of files to which coverage should be restricted.
    load_from_file: str, optional
        The name of the file, if any, that coverage information should be
        read from.

    Raises
    ------
    ValueError
        If coverage is restricted to the empty set of files.
    """
    restrict_to_files: Optional[FrozenSet[str]] = attr.ib(default=None)
    restrict_to_lines: Optional[Set[FileLine]] = attr.ib(default=None)
    load_from_file: Optional[str] = attr.ib(default=None)

    @restrict_to_files.validator
    def validate_restrict_to_files(self, attr, value) -> None:
        if value is None:
            return
        if not value:
            raise ValueError("cannot restrict to empty set of files")

    @restrict_to_lines.validator
    def validate_restrict_to_lines(self, attr, value) -> None:
        if value is None:
            return
        if not value:
            raise ValueError("cannot restrict to empty set of lines")

    @staticmethod
    def from_dict(d: Dict[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'CoverageConfig':
        restrict_to_files: Optional[FrozenSet[str]] = None
        restrict_to_lines: Optional[Set[FileLine]] = None
        load_from_file: Optional[str] = None
        if 'load-from-file' in d:
            load_from_file = d['load-from-file']
            assert load_from_file is not None
            if not os.path.isabs(load_from_file):
                assert dir_ is not None
                load_from_file = os.path.join(dir_, load_from_file)
        if 'restrict-to-files' in d:
            restrict_to_files_list: List[str] = d['restrict-to-files']
            restrict_to_files = frozenset(restrict_to_files_list)
        if 'restrict-to-lines' in d:
            restrict_to_lines = FileLineSet.from_dict(d['restrict-to-lines'])
        return CoverageConfig(restrict_to_files=restrict_to_files,
                              restrict_to_lines=restrict_to_lines,
                              load_from_file=load_from_file)


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
class SchemaConfig:
    name: str = attr.ib()

    @staticmethod
    def from_yml(yml) -> 'SchemaConfig':
        if not isinstance(yml, dict):
            m = "expected an object but was a {}".format(type(yml).__name__)
            m = "illegal schema description: {}".format(m)
            raise BadConfigurationException(m)
        if not 'type' in yml:
            m = "missing 'type' property in schema description"
            raise BadConfigurationException(m)

        name: str = yml['type']
        return SchemaConfig(name=name)


@attr.s(frozen=True)
class TransformationsConfig:
    """Specifies which transformations should be applied by the search."""
    schemas: Collection[SchemaConfig] = attr.ib(default=tuple())

    @staticmethod
    def from_yml(yml) -> 'TransformationsConfig':
        if not 'schemas' in yml:
            m = "'schemas' property missing in 'transformations' section"
            raise BadConfigurationException(m)
        if not isinstance(yml['schemas'], list):
            m = "'schemas' property should be a list"
            raise BadConfigurationException(m)

        schemas: Collection[SchemaConfig] = \
            tuple(SchemaConfig.from_yml(y) for y in yml['schemas'])
        return TransformationsConfig(schemas)


@attr.s(frozen=True)
class Config:
    """A configuration for Darjeeling.

    Attributes
    ----------
    snapshot: str
        The name of the BugZoo snapshot that should be repaired.
    language: Language
        The language that is used by the program under repair.
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
    tests: TestSuiteConfig
        A configuration for the test suite.
    """
    snapshot: str = attr.ib()
    language: Language = attr.ib()
    dir_patches: str = attr.ib()
    transformations: TransformationsConfig = attr.ib()
    localization: LocalizationConfig = attr.ib()
    search: SearcherConfig = attr.ib()
    tests: TestSuiteConfig = attr.ib()
    seed: int = attr.ib(default=0)
    optimizations: OptimizationsConfig = attr.ib(factory=OptimizationsConfig)
    coverage: CoverageConfig = attr.ib(factory=CoverageConfig)
    terminate_early: bool = attr.ib(default=True)
    threads: int = attr.ib(default=1)
    limit_candidates: Optional[int] = attr.ib(default=None)
    limit_time_minutes: Optional[float] = attr.ib(default=None)

    @dir_patches.validator
    def validate_dir_patches(self, attribute, value):
        if not os.path.isabs(value):
            m = "patch directory must be an absolute directory"
            raise BadConfigurationException(m)

    @seed.validator
    def validate_seed(self, attribute, value):
        if value < 0:
            m = "'seed' should be greater than or equal to zero."
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
                 limit_time_minutes: Optional[int] = None
                 ) -> 'Config':
        """Loads a configuration from a YAML dictionary.

        Raises
        ------
        BadConfigurationException
            If an illegal configuration is provided.
        """
        has_limits = 'resource-limits' in yml

        if 'snapshot' not in yml:
            raise BadConfigurationException("'snapshot' property is missing")
        if not isinstance(yml['snapshot'], str):
            m = "'snapshot' property should be a string"
            raise BadConfigurationException(m)
        snapshot: str = yml['snapshot']

        if threads is None and 'threads' in yml:
            if not isinstance(yml['threads'], int):
                m = "'threads' property should be an int"
                raise BadConfigurationException(m)
            threads = yml['threads']
        elif threads is None:
            threads = 1

        # no seed override; seed provided in config
        if seed is None and 'seed' in yml:
            if not isinstance(yml['seed'], int):
                m = "'seed' property should be an int."
                raise BadConfigurationException(m)
            seed = yml['seed']
        # no seed override or provided in config; use current date/time
        elif seed is None:
            random.seed(datetime.datetime.now())
            seed = random.randint(0, sys.maxsize)

        # determine the language
        if 'language' not in yml:
            m = "'language' property is missing"
            raise BadConfigurationException(m)
        if not isinstance(yml['language'], str):
            m = "'language' property should be a string"
            raise BadConfigurationException(m)
        try:
            language: Language = Language.find(yml['language'])
        except LanguageNotSupported:
            supported = ', '.join([l.value for l in Language])
            supported = "(supported languages: {})".format(supported)
            m = "unsupported language [{}]. {}"
            m = m.format(yml['language'], supported)
            raise BadConfigurationException(m)

        has_candidate_override = limit_candidates is not None
        has_candidate_limit = \
            has_limits and 'candidates' in yml['resource-limits']
        if not has_candidate_override and has_candidate_limit:
            if not isinstance(yml['resource-limits']['candidates'], int):
                m = "'candidates' property in 'resource-limits' section should be an int"
                raise BadConfigurationException(m)
            limit_candidates = yml['resource-limits']['candidates']

        has_time_override = limit_time_minutes is not None
        has_time_limit = \
            has_limits and 'time-minutes' in yml['resource-limits']
        if has_time_override and has_time_limit:
            if not isinstance(yml['resource-limits']['time-minutes'], int):
                m = "'time-minutes' property in 'resource-limits' section should be an int"  # noqa: pycodestyle
                raise BadConfigurationException(m)
            limit_time_minutes = yml['resource-limits']['time-minutes']

        opts = OptimizationsConfig.from_yml(yml.get('optimizations', {}))

        # coverage config
        if 'coverage' in yml:
            coverage = CoverageConfig.from_dict(yml['coverage'], dir_)
        else:
            coverage = CoverageConfig()

        # fetch the transformation schemas
        if 'transformations' not in yml:
            m = "'transformations' section is missing"
            raise BadConfigurationException(m)
        if not isinstance(yml['transformations'], dict):
            m = "'transformations' section should be an object"
            raise BadConfigurationException(m)
        transformations = \
            TransformationsConfig.from_yml(yml['transformations'])

        if 'localization' not in yml:
            m = "'localization' section is missing"
            raise BadConfigurationException(m)
        localization = LocalizationConfig.from_yml(yml['localization'])

        if 'algorithm' not in yml:
            m = "'algorithm' section is missing"
            raise BadConfigurationException(m)
        search = SearcherConfig.from_dict(yml['algorithm'], dir_)

        if 'tests' in yml and not isinstance(yml['tests'], dict):
            m = "'tests' section should be an object"
            raise BadConfigurationException(m)
        tests = TestSuiteConfig.from_dict(yml.get('tests', {}), dir_)

        return Config(snapshot=snapshot,
                      language=language,
                      seed=seed,
                      threads=threads,
                      terminate_early=terminate_early,
                      limit_time_minutes=limit_time_minutes,
                      limit_candidates=limit_candidates,
                      transformations=transformations,
                      localization=localization,
                      tests=tests,
                      coverage=coverage,
                      search=search,
                      optimizations=opts)
