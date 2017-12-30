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
                 content: str
                 ) -> None:
        self.__content = content

    @property
    def content(self) -> str:
        """
        Returns the contents of the snippet as a string.
        """
        return self.__content

    def __eq__(self, other) -> bool:
        return isinstance(other, Snippet) and self.content == other.content

    def __hash__(self) -> int:
        return hash(self.__content)


class DonorPool(object):
    @staticmethod
    def from_files(bug: Bug, filenames: List[str]) -> 'DonorPool':
        file_snippets = [DonorPool.from_file(bug, fn) for fn in filenames]
        all_snippets = [s for pool in file_snippets for s in pool]
        return DonorPool(all_snippets)

    @staticmethod
    def from_file(bug: Bug, filename: str) -> 'DonorPool':
        """
        Constructs a donor pool of snippets from the contents of a given file.
        """
        snippets = set()
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
                lines = [l for l in f]

            # create a snippet for each line
            for content in lines:
                # line = FileLine(filename, num)
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

                snippets.add(Snippet(content))

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
