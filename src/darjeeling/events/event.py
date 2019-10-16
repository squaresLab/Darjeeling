# -*- coding: utf-8 -*-
import attr as _attr

from ..core import (Test as _Test,
                    TestOutcome as _TestOutcome,
                    BuildOutcome as _BuildOutcome)
from ..candidate import Candidate as _Candidate
from ..outcome import CandidateOutcome as _CandidateOutcome


class DarjeelingEvent:
    """Base class used by all events within Darjeeling."""


@_attr.s(frozen=True, auto_attrs=True, slots=True)
class BuildStarted(DarjeelingEvent):
    """An attempt to build a candidate patch has started."""
    candidate: _Candidate


@_attr.s(frozen=True, auto_attrs=True, slots=True)
class BuildFinished(DarjeelingEvent):
    """An attempt to build a candidate patch has finished."""
    candidate: _Candidate
    outcome: _BuildOutcome


@_attr.s(frozen=True, auto_attrs=True, slots=True)
class TestExecutionStarted(DarjeelingEvent):
    """A test for a given candidate patch has started executing."""
    candidate: _Candidate
    test: _Test


@_attr.s(frozen=True, auto_attrs=True, slots=True)
class TestExecutionFinished(DarjeelingEvent):
    """A test for a given candidate patch has finished executing."""
    candidate: _Candidate
    test: _Test
    outcome: _TestOutcome


@_attr.s(frozen=True, auto_attrs=True, slots=True)
class CandidateEvaluationStarted(DarjeelingEvent):
    """Evaluation of a given candidate patch has started."""
    candidate: _Candidate


@_attr.s(frozen=True, auto_attrs=True, slots=True)
class CandidateEvaluationFinished(DarjeelingEvent):
    """Evaluation of a given candidate patch has finished."""
    candidate: _Candidate
    outcome: _CandidateOutcome
