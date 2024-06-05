__all__ = ("ResourceUsageTracker", "ResourceLimit", "ResourceLimits")

import abc
from collections.abc import Collection, Iterator, Mapping
from typing import Any, NoReturn, Optional

import attr
from loguru import logger

from . import exceptions as exc
from .util import Stopwatch


@attr.s(auto_attribs=True)
class ResourceUsageTracker:
    """Tracks resource usage over the course of the search.

    Attributes
    ----------
    limits: ResourceLimits
        Specifies limits on the resources that may be consumed.
    wall_clock: Stopwatch
        The amount of time spent searching for a patch.
    tests: int
        The number of test executions.
    candidates: int
        The number of candidate patch evaluations.
    """
    limits: "ResourceLimits"
    wall_clock: Stopwatch = attr.ib(factory=Stopwatch)
    tests: int = attr.ib(default=0)
    candidates: int = attr.ib(default=0)

    @staticmethod
    def with_limits(limits: "ResourceLimits") -> "ResourceUsageTracker":
        """Constructs a new tracker with given resource limits."""
        return ResourceUsageTracker(limits=limits)

    def check_limits(self) -> None:
        """Checks whether the resource limit has been reached, and if so,
        throws an exception.

        Raises
        ------
        ResourceLimitReached
            If a resource limit has been reached.
        """
        self.limits.check(self)


class ResourceLimit(abc.ABC):
    """Used to check if a particular resource limit is exceeded."""
    @abc.abstractmethod
    def check(self, usage: ResourceUsageTracker) -> None:
        """Checks if this limit has been reached, and raises an exception
        if indeed it has.
        """
        ...


@attr.s(frozen=True, str=False)
class ResourceLimits(ResourceLimit):
    limits: Collection[ResourceLimit] = attr.ib()

    @classmethod
    def from_dict(cls,
                  dict_: Mapping[str, Any],
                  dir_: Optional[str],
                  ) -> "ResourceLimits":
        logger.info(f"parsing resource limits: {dict_}")
        limits: list[ResourceLimit] = []

        def err(message: str) -> NoReturn:
            raise exc.BadConfigurationException(message)

        if "candidates" in dict_:
            if not isinstance(dict_["candidates"], int):
                err("'candidates' property in 'resource-limits' section "
                    "should be an int")
            limits.append(CandidateLimit(dict_["candidates"]))

        if "tests" in dict_:
            if not isinstance(dict_["tests"], int):
                err("'tests' property in 'resource-limits' section "
                    "should be an int")
            limits.append(TestLimit(dict_["tests"]))

        if "time-minutes" in dict_:
            if not isinstance(dict_["time-minutes"], int):
                err("'time-minutes' property in 'resource-limits' section "
                    "should be an int")
            limits.append(TimeLimit.minutes(dict_["time-minutes"]))

        return ResourceLimits(limits)

    def __iter__(self) -> Iterator[ResourceLimit]:
        """Returns an iterator over the individual resource limits."""
        yield from self.limits

    def __str__(self) -> str:
        if not self.limits:
            return "no resources limits"
        inner = "\n".join(f"* {limit!s}" for limit in self)
        return f"resource limits:\n{inner}"

    def check(self, usage: ResourceUsageTracker) -> None:
        for limit in self.limits:
            limit.check(usage)


@attr.s(frozen=True, str=False)
class CandidateLimit(ResourceLimit):
    """Imposes a limit on the number of candidate patch evaluations."""
    max_candidates: int = attr.ib()

    def __str__(self) -> str:
        return (f"maximum number of candidate patch "
                f"evaluations: {self.max_candidates}")

    @max_candidates.validator
    def validate_max_candidates(self, attribute, value) -> None:  # type: ignore
        if self.max_candidates < 1:
            message = ("maximum number of candidates must be equal to "
                       "or greater than one")
            raise exc.BadConfigurationException(message)

    def check(self, usage: ResourceUsageTracker) -> None:
        if usage.candidates >= self.max_candidates:
            raise exc.CandidateLimitReached


@attr.s(frozen=True, str=False)
class TestLimit(ResourceLimit):
    """Imposes a limit on the number of individual test executions."""
    max_executions: int = attr.ib()

    def __str__(self) -> str:
        return f"maximum number of test executions: {self.max_executions}"

    @max_executions.validator
    def validate_max_executions(self, attribute, value) -> None:  # type: ignore[no-untyped-def]
        if self.max_executions < 1:
            message = ("maximum number of test executions must be equal to "
                       "or greater than one")
            raise exc.BadConfigurationException(message)

    def check(self, usage: ResourceUsageTracker) -> None:
        if usage.tests >= self.max_executions:
            raise exc.TestLimitReached


@attr.s(frozen=True, str=False)
class TimeLimit(ResourceLimit):
    """Imposes a limit on the number of individual test executions."""
    max_seconds: float = attr.ib()

    def __str__(self) -> str:
        return f"wall-clock time limit: {self.max_seconds} seconds"

    @max_seconds.validator
    def validate_max_seconds(self, attribute, value) -> None:  # type: ignore[no-untyped-def]
        if self.max_seconds < 1:
            message = ("maximum number of seconds must be equal to "
                       "or greater than one second")
            raise exc.BadConfigurationException(message)

    @staticmethod
    def minutes(minutes: int) -> "TimeLimit":
        if minutes < 1:
            message = "time limit must be greater than or equal to one minute"
            raise exc.BadConfigurationException(message)
        return TimeLimit(minutes * 60)

    def check(self, usage: ResourceUsageTracker) -> None:
        if usage.wall_clock.duration >= self.max_seconds:
            raise exc.TimeLimitReached
