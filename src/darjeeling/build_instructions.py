# -*- coding: utf-8 -*-
__all__ = ('BuildStep', 'BuildInstructions')

from typing import Sequence, Optional, Tuple, Union, Mapping, Iterator

import attr
import bugzoo
import dockerblade
from dockerblade.stopwatch import Stopwatch

from . import exceptions as exc
from .container import ProgramContainer
from .environment import Environment


@attr.s(frozen=True, auto_attribs=True, slots=True)
class BuildStep:
    """Provides executable instructions for a build step."""
    command: str
    directory: str

    def execute(self,
                container: ProgramContainer,
                *,
                time_limit: Optional[int] = None
                ) -> None:
        """Applies this build step to a given container.
        
        Raises
        ------
        BuildStepFailed
            if the build step timed out or returned a non-zero code.
        """
        try:
            container.shell.check_call(self.command,
                                       cwd=self.directory,
                                       time_limit=time_limit)
        except dockerblade.exceptions.CalledProcessError as err:
            raise exc.BuildStepFailed(step=self,
                                      returncode=err.returncode,
                                      duration=err.duration,
                                      output=err.output)


@attr.s(frozen=True, auto_attribs=True, slots=True)
class BuildInstructions(Sequence[BuildStep]):
    """Provides executable instructions for building the program."""
    steps: Sequence[BuildStep]
    time_limit: Optional[int]

    @staticmethod
    def from_bugzoo(snapshot: bugzoo.Bug
                    ) -> Tuple['BuildInstructions', 'BuildInstructions']:
        """Extracts build instructions from a BugZoo object.

        Parameters
        ----------
        snapshot: bugzoo.Bug
            A BugZoo snapshot for a program.

        Returns
        -------
        Tuple[BuildInstructions, BuildInstructions]
            A tuple that contains, in order, instructions for building the
            associated program, and a set of instructions for building the
            program with coverage instrumentation.
        """
        compiler = snapshot.compiler
        if not compiler.context:
            workdir = snapshot.source_directory
        else:
            workdir = compiler.context

        build_instructions = \
            BuildInstructions(
                steps=(BuildStep(command=compiler.command,
                                 directory=workdir),),
                time_limit=compiler.time_limit)

        build_instructions_for_coverage = \
            BuildInstructions(
                steps=(BuildStep(command=compiler.command_with_instrumentation,
                                 directory=workdir),),
                time_limit=compiler.time_limit)

        return build_instructions, build_instructions_for_coverage

    def __len__(self) -> int:
        """Returns the number of build steps."""
        return len(self.steps)

    def __iter__(self) -> Iterator[BuildStep]:
        """Returns an iterator over the build steps."""
        yield from self.steps

    def __getitem__(self, index):
        """Returns the n-th build step from these instructions."""
        return self.steps[index]

    def __call__(self, container: ProgramContainer) -> None:
        """Executes these build instructions in a given container."""
        self.execute(container)

    def execute(self, container: ProgramContainer) -> None:
        """Executes these build instructions in a given container."""
        with Stopwatch() as timer:
            for step in self.steps:
                time_left: Optional[int] = None
                if self.time_limit:
                    time_left = int(max(0, timer - self.time_limit))
                step.execute(container, time_limit=time_left)
