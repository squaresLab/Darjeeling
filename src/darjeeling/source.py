from typing import List, Iterator
import os
import tempfile
import difflib

import bugzoo
from bugzoo.core.bug import Bug
from bugzoo.core.patch import FilePatch


class SourceFile(object):
    # FIXME refactor
    @staticmethod
    def load(bz: bugzoo.BugZoo, bug: Bug, filename: str) -> 'SourceFile':
        """
        Loads a specified source-code file belonging to a provided faulty
        program version.
        """
        container = bz.containers.provision(bug)
        fd, host_fn = tempfile.mkstemp()
        try:
            os.close(fd)
            container_fn = os.path.join(bug.source_dir, filename)
            bz.containers.copy_from(container, container_fn, host_fn)

            with open(host_fn, 'r') as f:
                lines = [l.rstrip('\n') for l in f]
                return SourceFile(filename, lines)
        finally:
            del bz.containers[container.uid]
            os.remove(host_fn)

    def __init__(self, name: str, lines: List[str]) -> None:
        self.__name = name
        self.__lines = lines[:]

    @property
    def name(self) -> str:
        """
        The name of this source code file.
        """
        return self.__name

    @property
    def lines(self) -> List[str]:
        """
        Returns a copy of the lines contained within this file.
        """
        return self.__lines[:]

    def __getitem__(self, num: int) -> str:
        """
        Retrieves the contents of a given line in this file, specified by its
        one-indexed line number.
        """
        return self.__lines[num - 1]

    def __iter__(self) -> Iterator[str]:
        """
        Returns an iterator over the lines contained within this file.
        """
        for line in self.__lines:
            yield line

    def __len__(self) -> int:
        """
        Returns a count of the number of lines in this file.
        """
        return len(self.__lines)

    def with_line_removed(self, num: int) -> 'SourceFile':
        """
        Returns a variant of this file with a given line, specified by its
        one-indexed line number, removed.
        """
        num -= 1
        l2 = self.__lines[0:num] + self.__lines[num + 1:]
        return SourceFile(self.name, l2)

    def with_line_replaced(self, num: int, replacement: str) -> 'SourceFile':
        """
        Returns a variant of this file with the contents of a given line,
        specified by its one-indexed line number, replaced by a provided string.
        """
        num -= 1
        l2 = self.__lines[:]
        l2[num] = replacement
        return SourceFile(self.name, l2)

    def with_line_inserted(self, num: int, insertion: str) -> 'SourceFile':
        """
        Returns a variant of this file with a given line inserted at a
        specified location.
        """
        num -= 1
        l2 = self.__lines[:]
        l2.insert(num, insertion)
        return SourceFile(self.name, l2)

    def diff(self,
             other: 'SourceFile'
             ) -> str:
        a = ['{}\n'.format(l) for l in self.__lines]
        b = ['{}\n'.format(l) for l in other.lines]
        diff_lines = difflib.unified_diff(a, b,
                                          fromfile=self.name,
                                          tofile=other.name)
        return ''.join(diff_lines)
