import os
import tempfile
from typing import List, Iterator
from bugzoo import Bug
from bugzoo.coverage import FileLine
from tempfile import NamedTemporaryFile


class Snippet(object):
    """
    Represents a donor code snippet.
    """
    def __init__(self,
                 line: FileLine,
                 content: str
                 ) -> None:
        self.__line = line
        self.__content = content

    @property
    def line(self) -> FileLine:
        return self.__line

    @property
    def content(self) -> str:
        """
        Returns the contents of the snippet as a string.
        """
        return self.__content


class DonorPool(object):
    @staticmethod
    def from_file(bug: Bug, filename: str) -> 'DonorPool':
        """
        Constructs a donor pool of snippets from the contents of a given file.
        """
        snippets = []
        container = bug.provision()
        fd, host_fn = tempfile.mkstemp()
        try:
            # copy the source file from the container and to a temporary file
            # on the host machine.
            os.close(fd)
            container_fn = os.path.join(bug.source_dir, filename)
            container.copy_from(container_fn, host_fn)

            # fetch a list of source code lines
            with open(host_fn, 'r') as f:
                lines = [l.rstrip('\n') for l in f]

            # create a snippet for each line
            for (num, content) in enumerate(lines, 1):
                line = FileLine(filename, num)
                content = content.strip()

                # comments
                if content.startswith('/*') or content.startswith('/'):
                    continue

                # macros
                if content.startswith('#'):
                    continue

                # restrict to statements
                if not content.endswith(';'):
                    continue

                snippets.append(Snippet(line, content))

        finally:
            container.destroy()
            os.remove(host_fn)

        return DonorPool(snippets)

    def __init__(self, snippets: List[Snippet]):
        self.__snippets = snippets

    def __iter__(self) -> Iterator[Snippet]:
        """
        Returns an iterator over the snippets contained in this donor pool.
        """
        for snippet in self.__snippets:
            yield snippet
