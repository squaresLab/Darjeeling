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
class TestExecutionFinished:
    """A test for a given candidate patch has finished executing."""
    candidate: _Candidate
    test: _Test
    outcome: _TestOutcome
