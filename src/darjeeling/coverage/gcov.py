# -*- coding: utf-8 -*-
__all__ = ('GCovCollector',)

from typing import FrozenSet, Mapping, Any, Set, Dict, Optional, ClassVar
import os
import typing
import xml.etree.ElementTree as ET

from loguru import logger
import attr

from .collector import CoverageCollector, CoverageCollectorConfig
from ..core import FileLineSet

if typing.TYPE_CHECKING:
    from ..container import ProgramContainer
    from ..environment import Environment
    from ..program import ProgramDescription

_INSTRUMENTATION = (
    "/* DARJEELING :: INSTRUMENTATION :: START */\n"
    "#include <stdio.h>\n"
    "#include <stdlib.h>\n"
    "#include <signal.h>\n"
    "#ifdef __cplusplus\n"
    "  extern \"C\" void __gcov_flush(void);\n"
    "#else\n"
    "  void __gcov_flush(void);\n"
    "#endif\n"
    "void darjeeling_sighandler(int sig){\n"
    "  __gcov_flush();\n"
    "  if(sig != SIGUSR1 && sig != SIGUSR2)\n"
    "    exit(1);\n"
    "}\n"
    "void darjeeling_ctor (void) __attribute__ ((constructor));\n"
    "void darjeeling_ctor (void) {\n"
    "  struct sigaction new_action;\n"
    "  new_action.sa_handler = darjeeling_sighandler;\n"
    "  sigemptyset(&new_action.sa_mask);\n"
    "  new_action.sa_flags = 0;\n"
    "  sigaction(SIGTERM, &new_action, NULL);\n"
    "  sigaction(SIGINT, &new_action, NULL);\n"
    "  sigaction(SIGKILL, &new_action, NULL);\n"
    "  sigaction(SIGSEGV, &new_action, NULL);\n"
    "  sigaction(SIGFPE, &new_action, NULL);\n"
    "  sigaction(SIGBUS, &new_action, NULL);\n"
    "  sigaction(SIGILL, &new_action, NULL);\n"
    "  sigaction(SIGABRT, &new_action, NULL);\n"
    "  /* Use signal for SIGUSR to remove handlers */\n"
    "  signal(SIGUSR1, darjeeling_sighandler);\n"
    "  signal(SIGUSR2, darjeeling_sighandler);\n"
    "}\n"
    "/* DARJEELING :: INSTRUMENTATION :: END */\n"
)
_NUM_INSTRUMENTATION_LINES = _INSTRUMENTATION.count('\n')
_LINES_TO_REMOVE = set(range(1, _NUM_INSTRUMENTATION_LINES))


@attr.s(frozen=True, slots=True, auto_attribs=True)
class GCovCollectorConfig(CoverageCollectorConfig):
    NAME: ClassVar[str] = 'gcov'
    files_to_instrument: FrozenSet[str]

    @classmethod
    def from_dict(self,
                  dict_: Mapping[str, Any],
                  dir_: Optional[str] = None
                  ) -> 'CoverageCollectorConfig':
        assert dict_['type'] == 'gcov'
        files_to_instrument = frozenset(dict_.get('files-to-instrument', []))
        return GCovCollectorConfig(files_to_instrument=files_to_instrument)

    def _find_source_filenames(self,
                               program: 'ProgramDescription'
                               ) -> FrozenSet[str]:
        """Determines the set of all source files within a program."""
        with program.provision() as container:
            source_directory = program.source_directory
            endings = ('.cpp', '.cc', '.c', '.h', '.hh', '.hpp', '.cxx')
            command = ' -o '.join([f"-name \*{e}" for e in endings])
            command = f'find {source_directory} -type f \( {command} \)'
            output = container.shell.check_output(command, text=True)
            return frozenset(filename.strip() for filename in output.split('\n'))

    def build(self,
              environment: 'Environment',
              program: 'ProgramDescription'
              ) -> 'CoverageCollector':
        source_directory = program.source_directory
        source_filenames = self._find_source_filenames(program)
        files_to_instrument = frozenset(
            fn if os.path.isabs(fn) else os.path.join(source_directory, fn)
            for fn in self.files_to_instrument)

        collector = GCovCollector(environment=environment,
                                  program=program,
                                  source_directory=source_directory,
                                  source_filenames=source_filenames,
                                  files_to_instrument=files_to_instrument)
        logger.trace(f"built coverage collector: {collector}")
        return collector


@attr.s(frozen=True, slots=True, auto_attribs=True)
class GCovCollector(CoverageCollector):
    program: 'ProgramDescription'
    _source_directory: str
    _files_to_instrument: FrozenSet[str]
    _source_filenames: FrozenSet[str]
    _environment: 'Environment' = attr.ib(repr=False)

    def _read_line_coverage_for_class(self, xml_class: ET.Element) -> Set[int]:
        xml_lines = xml_class.find('lines')
        assert xml_lines
        lines = xml_lines.findall('line')
        return set(int(l.attrib['number']) for l in lines
                   if int(l.attrib['hits']) > 0)

    def _corrected_lines(self,
                         relative_filename: str,
                         lines: Set[int]
                         ) -> Set[int]:
        if os.path.isabs(relative_filename):
            absolute_filename = relative_filename
        else:
            absolute_filename = os.path.join(self._source_directory, relative_filename)

        if absolute_filename not in self._files_to_instrument:
            logger.trace(f"file was not instrumented: {absolute_filename}")
            return lines

        lines = lines - _LINES_TO_REMOVE
        return set(i - _NUM_INSTRUMENTATION_LINES for i in lines)

    def _has_source_file(self, filename_relative: str) -> bool:
        source_directory = self._source_directory
        filename_absolute = os.path.join(source_directory, filename_relative)
        return filename_absolute in self._source_filenames

    # FIXME is this a general solution?
    def _resolve_filepath(self, filename_relative: str) -> str:
        if not filename_relative:
            raise ValueError('failed to resolve path')
        if self._has_source_file(filename_relative):
            return filename_relative

        filename_relative_child = '/'.join(filename_relative.split('/')[1:])
        return self._resolve_filepath(filename_relative_child)

    def _parse_xml_report(self, root: ET.Element) -> FileLineSet:
        packages_node = root.find('packages')
        assert packages_node
        package_nodes = packages_node.findall('package')
        class_nodes = [c for p in package_nodes for c in p.find('classes').findall('class')]  # type: ignore

        filename_to_lines: Dict[str, Set[int]] = {}
        for node in class_nodes:
            filename = node.attrib['filename']
            try:
                filename_original = filename
                filename = self._resolve_filepath(filename)
                logger.trace(f"resolving path '{filename_original}' "
                             f"-> '{filename}'")
            except ValueError:
                logger.warning(f'failed to resolve file: {filename}')
                continue

            lines = self._read_line_coverage_for_class(node)
            lines = self._corrected_lines(filename, lines)
            if lines:
                filename_to_lines[filename] = lines

        return FileLineSet(filename_to_lines)

    def _parse_xml_file_contents(self, contents: str) -> FileLineSet:
        logger.trace(f"Parsing gcovr report:\n{contents}")
        root = ET.fromstring(contents)
        return self._parse_xml_report(root)

    def _extract(self, container: 'ProgramContainer') -> FileLineSet:
        files = container.filesystem
        shell = container.shell
        temporary_filename = files.mktemp()

        command = f'gcovr -o "{temporary_filename}" -x -d -r .'
        shell.check_call(command, cwd=self._source_directory)
        xml_file_contents = files.read(temporary_filename)

        return self._parse_xml_file_contents(xml_file_contents)

    def _prepare(self, container: 'ProgramContainer') -> None:
        """
        Adds source code instrumentation and recompiles the program inside
        a container using the appropriate GCC options. Also ensures that
        gcovr is installed inside the container.
        """
        files = container.filesystem
        for filename in self._files_to_instrument:
            logger.trace(f'adding gcov instrumentation to {filename}')
            contents_original = files.read(filename)
            logger.trace(f'original file [{filename}]:\n{contents_original}')
            contents_instrumented = _INSTRUMENTATION + contents_original
            logger.trace(f'instrumented file [{filename}]:\n{contents_instrumented}')
            files.write(filename, contents_instrumented)

        build_instructions = self.program.build_instructions_for_coverage
        build_instructions.execute(container)
