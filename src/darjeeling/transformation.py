from typing import List, Iterator, Dict

from bugzoo.core.bug import Bug
from bugzoo.core.coverage import FileLine

from darjeeling.donor import Snippet, DonorPool
from darjeeling.source import SourceFile


class Transformation(object):
    @property
    def diff(self) -> str:
        raise NotImplementedError


class DeleteTransformation(object):
    def __init__(self, line: FileLine) -> None:
        self.__line = line

    @property
    def line(self) -> FileLine:
        return self.__line

    def __str__(self) -> str:
        return "DELETE[{}]".format(self.__line)


class ReplaceTransformation(object):
    """
    Replaces a numbered line in a given file with a provided snippet.
    """
    def __init__(self, line: FileLine, snippet: Snippet) -> None:
        self.__line = line
        self.__snippet = snippet

    @property
    def line(self) -> FileLine:
        return self.__line

    @property
    def snippet(self) -> Snippet:
        return self.__snippet

    def __str__(self) -> str:
        return "REPLACE[{}; {}]".format(self.__line, self.__snippet)


class AppendTransformation(object):
    """
    Appends a given snippet to a specific line in a given file.
    """
    def __init__(self, line: FileLine, snippet: Snippet) -> None:
        self.__line = line
        self.__snippet = snippet

    @property
    def snippet(self) -> Snippet:
        return self.__snippet

    @property
    def line(self) -> FileLine:
        return self.__line

    def __str__(self) -> str:
        return "APPEND[{}; {}]".format(self.__line, self.__snippet)


class TransformationDatabase(object):
    """
    Used to represent the space of all atomic program transformations.
    """
    @staticmethod
    def generate(bug: Bug,
                 pool: DonorPool,
                 sources: Dict[str, SourceFile],
                 lines: List[FileLine]) -> None:
        transformations = []
        for line in lines:
            # get the content of the line
            original_line = sources[line.filename][line.num].strip()

            # ignore any line that might not be a statement
            if not original_line.endswith(';'):
                continue

            # ignore comments and macros (probably redundant)
            if original_line.startswith('#') or \
               original_line.startswith('//') or \
               original_line.startswith('/*') \
            :
               continue

            # deletion
            transformations.append(DeleteTransformation(line))

            # replace and append
            for snippet in pool:
                transformations.append(AppendTransformation(line, snippet))

                # don't replace a line with an equivalent one
                if snippet.content != original_line:
                    transformations.append(ReplaceTransformation(line, snippet))

        return TransformationDatabase(transformations)

    def __init__(self, transformations: List[Transformation]):
        self.__transformations = transformations[:]

    def __len__(self) -> int:
        return len(self.__transformations)

    def __iter__(self) -> Iterator[Transformation]:
        """
        Returns an iterator over the transformations contained within this
        database.
        """
        for t in self.__transformations:
            yield t

    def at_line(self, line: FileLine) -> Iterator[Transformation]:
        """
        Returns an iteratover over all the transformations at a given line.
        """
        raise NotImplementedError
