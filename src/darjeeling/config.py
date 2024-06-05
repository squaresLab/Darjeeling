from __future__ import annotations

__all__ = (
    "Config",
    "CoverageConfig",
    "LocalizationConfig",
    "OptimizationsConfig",
)

import datetime
import os
import random
import sys
import typing as t
from collections.abc import Collection
from typing import Any, NoReturn, Optional

import attr

from darjeeling.core import FileLine, FileLineSet
from darjeeling.coverage.config import CoverageConfig
from darjeeling.exceptions import BadConfigurationException
from darjeeling.program import ProgramDescriptionConfig
from darjeeling.resources import ResourceLimits
from darjeeling.searcher.config import SearcherConfig
from darjeeling.transformation.config import ProgramTransformationsConfig


@attr.s(frozen=True)
class LocalizationConfig:
    metric: str = attr.ib()  # FIXME validate
    exclude_files: Collection[str] = attr.ib(factory=frozenset)
    exclude_lines: Collection[FileLine] = attr.ib(factory=frozenset)
    restrict_to_files: Collection[str] | None = attr.ib(default=None)
    restrict_to_lines: Collection[FileLine] | None = attr.ib(default=None)

    @restrict_to_files.validator
    def validate_restrict_to_files(
        self,
        attribute: attr.Attribute[Collection[str] | None],
        value: Collection[str] | None,
    ) -> None:
        if value is not None and not value:
            m = "cannot restrict to empty set of files"
            raise BadConfigurationException(m)

    @restrict_to_files.validator
    def validate_restrict_to_lines(
        self,
        attribute: attr.Attribute[Collection[FileLine] | None],
        value: Collection[FileLine] | None,
    ) -> None:
        if value is not None and not value:
            m = "cannot restrict to empty set of lines"
            raise BadConfigurationException(m)

    @staticmethod
    def from_yml(yml: dict[str, Any]) -> LocalizationConfig:
        if not isinstance(yml, dict):
            m = "'localization' section should be an object"
            raise BadConfigurationException(m)
        if "metric" not in yml:
            m = "'metric' property is missing from 'localization' section"
            raise BadConfigurationException(m)
        if not isinstance(yml["metric"], str):
            m = "'metric' property in 'localization' should be a string"
            raise BadConfigurationException(m)

        metric: str = yml["metric"]
        exclude_files: Collection[str] = yml.get("exclude-files", [])
        restrict_to_files = yml.get("restrict-to-files")

        exclude_lines_arg: dict[str, list[int]] = yml.get("exclude-lines", {})
        exclude_lines: set[FileLine] = set()
        for fn in exclude_lines_arg:
            for line_num in exclude_lines_arg[fn]:
                exclude_lines.add(FileLine(fn, line_num))

        restrict_lines_arg = yml.get("restrict-to-lines")
        restrict_to_lines: t.AbstractSet[FileLine] | None = None
        if restrict_lines_arg is not None:
            restrict_to_lines = set()
            assert restrict_to_lines is not None  # mypy is stupid
            for fn in restrict_lines_arg:
                for line_num in restrict_lines_arg[fn]:
                    restrict_to_lines.add(FileLine(fn, line_num))
            restrict_to_lines = FileLineSet.from_iter(restrict_to_lines)

        return LocalizationConfig(
            metric=metric,
            exclude_files=exclude_files,
            exclude_lines=exclude_lines,
            restrict_to_files=restrict_to_files,
            restrict_to_lines=restrict_to_lines,
        )


@attr.s(frozen=True)
class OptimizationsConfig:
    """Specifies which optimizations should be applied during search."""
    use_scope_checking: bool = attr.ib(default=False)
    use_syntax_scope_checking: bool = attr.ib(default=True)
    ignore_dead_code: bool = attr.ib(default=False)
    ignore_equivalent_insertions: bool = attr.ib(default=False)
    ignore_untyped_returns: bool = attr.ib(default=False)
    ignore_string_equivalent_snippets: bool = attr.ib(default=False)
    ignore_decls: bool = attr.ib(default=True)
    only_insert_executed_code: bool = attr.ib(default=False)

    @staticmethod
    def from_yml(yml: dict[str, Any]) -> OptimizationsConfig:
        return OptimizationsConfig(
            use_scope_checking=yml.get("use-scope-checking", True),
            use_syntax_scope_checking=yml.get("use-syntax-scope-checking", True),
            ignore_dead_code=yml.get("ignore-dead-code", True),
            ignore_equivalent_insertions=yml.get("ignore-equivalent-insertions", True),
            ignore_untyped_returns=yml.get("ignore-untyped-returns", True),
            ignore_string_equivalent_snippets=yml.get("ignore-string-equivalent-snippets", True),
            ignore_decls=yml.get("ignore-decls", True),
            only_insert_executed_code=yml.get("only-insert-executed-code", True),
        )


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
    run_redundant_tests: bool
        Specifies if redundant tests should be run. Tests are deemed
        redundant if a candidate patch does not change lines that the
        test uses. Lines used are determined by test coverage.
    resource_limits: ResourceLimits
        Limits on the resources that may be consumed during the search.
    limit_time_minutes: int, optional
        An optional limit on the number of minutes that may be spent
        searching for an acceptable patch.
    search: SearcherConfig
        The configuration used by the search algorithm.
    program: ProgramDescriptionConfig
        A description of the program under transformation.
    transformations: ProgramTransformationsConfig
        A description of the transformation space.
    """
    dir_patches: str = attr.ib()
    program: ProgramDescriptionConfig
    transformations: ProgramTransformationsConfig
    localization: LocalizationConfig
    search: SearcherConfig
    coverage: CoverageConfig
    resource_limits: ResourceLimits
    seed: int = attr.ib(default=0)
    optimizations: OptimizationsConfig = attr.ib(factory=OptimizationsConfig)
    terminate_early: bool = attr.ib(default=True)
    threads: int = attr.ib(default=1)
    run_redundant_tests: bool = attr.ib(default=False)

    @seed.validator
    def validate_seed(self, _attribute: attr.Attribute[int], value: int) -> None:
        if value < 0:
            m = "'seed' should be greater than or equal to zero."
            raise BadConfigurationException(m)

    @dir_patches.validator
    def validate_patches(self, _attribute: attr.Attribute[str], value: str) -> None:
        if not os.path.isabs(value):
            m = "patch directory should be an absolute path."
            raise BadConfigurationException(m)

    @threads.validator
    def validate_threads(self, attribute: attr.Attribute[int], value: int) -> None:
        if value < 1:
            m = "number of threads must be greater than or equal to 1."
            raise BadConfigurationException(m)

    @staticmethod
    def from_yml(
        yml: dict[str, Any],
        dir_: Optional[str] = None,
        *,
        terminate_early: bool = True,
        seed: Optional[int] = None,
        threads: Optional[int] = None,
        run_redundant_tests: bool = False,
        limit_candidates: Optional[int] = None,
        limit_time_minutes: Optional[int] = None,
        dir_patches: Optional[str] = None,
    ) -> Config:
        """Loads a configuration from a YAML dictionary.

        Raises
        ------
        BadConfigurationException
            If an illegal configuration is provided.
        """
        def err(m: str) -> NoReturn:
            raise BadConfigurationException(m)

        if dir_patches is None and "save-patches-to" in yml:
            dir_patches = yml["save-patches-to"]
            if not isinstance(dir_patches, str):
                err("'save-patches-to' property should be a string")
            if not os.path.isabs(dir_patches):
                if not dir_:
                    err("'save-patches-to' must be absolute for non-file-based configurations")
                dir_patches = os.path.join(dir_, dir_patches)
        elif dir_patches is None:
            if not dir_:
                err("'save-patches-to' must be specified for non-file-based configurations")
            dir_patches = os.path.join(dir_, "patches")

        if threads is None and "threads" in yml:
            if not isinstance(yml["threads"], int):
                err("'threads' property should be an int")
            threads = yml["threads"]
        elif threads is None:
            threads = 1

        if "run-redundant-tests" in yml:
            if not isinstance(yml["run-redundant-tests"], bool):
                err("'run-redundant-tests' property should be an bool")
            run_redundant_tests = yml["run-redundant-tests"]

        # no seed override; seed provided in config
        if seed is None and "seed" in yml:
            if not isinstance(yml["seed"], int):
                err("'seed' property should be an int.")
            seed = yml["seed"]
        # no seed override or provided in config; use current date/time
        elif seed is None:
            random.seed(datetime.datetime.now().timestamp())
            seed = random.randint(0, sys.maxsize)

        # resource limits
        yml.setdefault("resource-limits", {})
        if limit_candidates is not None:
            yml["resource-limits"]["candidates"] = limit_candidates
        if limit_time_minutes is not None:
            yml["resource-limits"]["time-minutes"] = limit_time_minutes
        resource_limits = \
            ResourceLimits.from_dict(yml["resource-limits"], dir_)

        opts = OptimizationsConfig.from_yml(yml.get("optimizations", {}))

        # coverage config
        if "coverage" in yml:
            coverage = CoverageConfig.from_dict(yml["coverage"], dir_)
        else:
            m = "'coverage' section is expected"
            raise BadConfigurationException(m)

        # fetch the transformation schemas
        if "transformations" not in yml:
            err("'transformations' section is missing")
        if not isinstance(yml["transformations"], dict):
            err("'transformations' section should be an object")
        transformations = \
            ProgramTransformationsConfig.from_dict(yml["transformations"], dir_)

        if "localization" not in yml:
            err("'localization' section is missing")
        localization = LocalizationConfig.from_yml(yml["localization"])

        if "algorithm" not in yml:
            err("'algorithm' section is missing")
        search = SearcherConfig.from_dict(yml["algorithm"], dir_)

        if "program" not in yml:
            err("'program' section is missing")
        program = ProgramDescriptionConfig.from_dict(yml["program"], dir_)

        return Config(seed=seed,
                      threads=threads,
                      run_redundant_tests=run_redundant_tests,
                      terminate_early=terminate_early,
                      resource_limits=resource_limits,
                      transformations=transformations,
                      program=program,
                      localization=localization,
                      coverage=coverage,
                      search=search,
                      optimizations=opts,
                      dir_patches=dir_patches)
