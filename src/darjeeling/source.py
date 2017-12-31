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
