# -*- coding: utf-8 -*-
__all__ = ('BuildStep', 'BuildInstructions')

import typing as t

import attr
import bugzoo
import dockerblade
from dockerblade.stopwatch import Stopwatch
from loguru import logger

from . import exceptions as exc
from .container import ProgramContainer


@attr.s(frozen=True, auto_attribs=True, slots=True)
class BuildStep:
    """Provides executable instructions for a build step."""
    command: str
    directory: str

    @staticmethod
    def from_dict(dict_: t.Union[str, t.Mapping[str, t.Any]],
                  source_directory: str
                  ) -> 'BuildStep':
        def err(message: str) -> t.NoReturn:
            raise exc.BadConfigurationException(message)

        if isinstance(dict_, str):
            return BuildStep(dict_, source_directory)

        if 'command' not in dict_:
            err("build step is missing 'command' property")
        if not isinstance(dict_['command'], str):
            err("'command' property must be a string")
        command = dict_['command']

        if 'directory' not in dict_:
            directory = source_directory
        elif not isinstance(dict_['directory'], str):
            err("'directory' property must be a string")
        else:
            directory = dict_['directory']

        return BuildStep(command, directory)

    def execute(
        self,
        container: ProgramContainer,
        *,
        time_limit: t.Optional[int] = None,
        environment: t.Optional[t.Mapping[str, str]] = None,
    ) -> None:
        """Applies this build step to a given container.

        Raises
        ------
        BuildStepFailed
            if the build step timed out or returned a non-zero code.
        """
        try:
            outcome = container.shell.run(
                self.command,
                cwd=self.directory,
                time_limit=time_limit,
                environment=environment,
                text=True,
            )
            outcome.check_returncode()
        except dockerblade.exceptions.CalledProcessError as err:
            output: t.Optional[str]
            if err.output is None:
                output = None
            elif isinstance(err.output, str):
                output = err.output
            else:
                output = err.output.decode('utf-8')
            logger.trace(f"build output: {output}")
            raise exc.BuildStepFailed(step=self,
                                      returncode=err.returncode,
                                      duration=err.duration,
                                      output=output)


@attr.s(frozen=True, auto_attribs=True, slots=True)
class BuildInstructions(t.Sequence[BuildStep]):
    """Provides executable instructions for building the program."""
    steps: t.Sequence[BuildStep]
    time_limit: t.Optional[int]

    @staticmethod
    def from_dict(
        dict_: t.Mapping[str, t.Any],
        source_directory: str
    ) -> t.Tuple['BuildInstructions', 'BuildInstructions']:
        def err(message: str) -> t.NoReturn:
            raise exc.BadConfigurationException(message)

        if not isinstance(dict_, dict):
            err("'build-instructions' section should be an object")
        if 'steps' not in dict_:
            err("'steps' property is missing from 'build-instructions' section")
        if 'time-limit' not in dict_:
            err("'time-limit' property is missing from 'build-instructions' section")

        if not isinstance(dict_['time-limit'], int):
            err("'time-limit' property should be an int")
        time_limit: int = dict_['time-limit']

        if not isinstance(dict_['steps'], list):
            err("'steps' property should be an array")
        steps = tuple(BuildStep.from_dict(dict_step, source_directory)
                      for dict_step in dict_['steps'])

        if 'steps-for-coverage' in dict_:
            if not isinstance(dict_['steps-for-coverage'], list):
                err("'steps-for-coverage' property should be an array")

            steps_for_coverage = tuple(BuildStep.from_dict(dict_step, source_directory)
                                       for dict_step in dict_['steps-for-coverage'])
        else:
            steps_for_coverage = steps

        instructions = BuildInstructions(steps, time_limit)
        instructions_for_coverage = BuildInstructions(steps_for_coverage, time_limit)
        return instructions, instructions_for_coverage

    @staticmethod
    def from_bugzoo(
        snapshot: bugzoo.Bug
    ) -> t.Tuple['BuildInstructions', 'BuildInstructions']:
        """Extracts build instructions from a BugZoo object.

        Parameters
        ----------
        snapshot: bugzoo.Bug
            A BugZoo snapshot for a program.

        Returns
        -------
        t.Tuple[BuildInstructions, BuildInstructions]
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

    def __iter__(self) -> t.Iterator[BuildStep]:
        """Returns an iterator over the build steps."""
        yield from self.steps

    def __getitem__(self, index):
        """Returns the n-th build step from these instructions."""
        return self.steps[index]

    def __call__(self, container: ProgramContainer) -> None:
        """Executes these build instructions in a given container."""
        self.execute(container)

    def execute(
        self,
        container: ProgramContainer,
        *,
        environment: t.Optional[t.Mapping[str, str]] = None,
    ) -> None:
        """Executes these build instructions in a given container."""
        with Stopwatch() as timer:
            for step in self.steps:
                time_left: t.Optional[int] = None
                if self.time_limit:
                    time_left = int(max(0, timer.duration - self.time_limit))
                step.execute(
                    container,
                    time_limit=time_left,
                    environment=environment,
                )
