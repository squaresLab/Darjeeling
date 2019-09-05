# -*- coding: utf-8 -*-
__all__ = ('Config', 'OptimizationsConfig')

from typing import Optional
import random
import datetime

import attr

from .core import Language
from .exceptions import BadConfigurationException, LanguageNotSupported


@attr.s
class Config:
    """A configuration for Darjeeling.

    Attributes
    ----------
    snapshot: str
        The name of the BugZoo snapshot that should be repaired.
    language: Language
        The language that is used by the program under repair.
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
    """
    snapshot: str = attr.ib()
    language: Language = attr.ib()
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

    @threads.validator
    def validate_threads(self, attribute, value):
        if value < 1:
            m = "number of threads must be greater than or equal to 1."
            raise BadConfigurationException(m)

    @staticmethod
    def from_yml(yml: Dict[str, Any],
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
            random.seed(datetime.now())
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

        opts = OptimizationsConfig.from_yml(yml.get('optimizations', {}))

        return Config(snapshot=snapshot,
                      language=language,
                      seed=seed,
                      threads=threads,
                      optimizations=opts)


@attr.s
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


@attr.s
class TransformationsConfig:
    """Specifies which transformations should be applied by the search."""
    schemas: Collection[TransformationsConfig] = attr.ib(converter=tuple)
