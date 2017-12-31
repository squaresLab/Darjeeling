import os
import tempfile
from typing import List, Iterator
from bugzoo import Bug


class SourceFile(object):
    @staticmethod
    def load(bug: Bug, filename: str) -> 'SourceFile':
        """
        Loads a specified source-code file belonging to a provided faulty
        program version.
        """
        container = bug.provision()
        fd, host_fn = tempfile.mkstemp()
        try:
            os.close(fd)
            container_fn = os.path.join(bug.source_dir, filename)
            container.copy_from(container_fn, host_fn)

            with open(host_fn, 'r') as f:
                lines = [l.rstrip('\n') for l in f]
                return SourceFile(lines)
        finally:
            container.destroy()
            os.remove(host_fn)

    def __init__(self, lines: List[str]) -> None:
        self.__lines = lines[:]

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
        l2 = self.__lines[0:num] + self.__lines[num + 1:-1]
        return SourceFile(l2)

    def with_line_replaced(self, num: int, replacement: str) -> 'SourceFile':
        """
        Returns a variant of this file with the contents of a given line,
        specified by its one-indexed line number, replaced by a provided string.
        """
        num -= 1
        l2 = self.__lines[:]
        l2[num] = replacement
        return SourceFile(l2)

    def with_line_inserted(self, num: int, insertion: str) -> 'SourceFile':
        """
        Returns a variant of this file with a given line inserted at a
        specified location.
        """
        num -= 1
        l2 = self.__lines[:]
        l2.insert(num, insertion)
        return SourceFile(l2)
