from typing import List
from bugzoo.bug import Bug
from bugzoo.coverage import FileLine
from darjeeling.donor import DonorPool
from darjeeling.donor import Snippet, DonorPool


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


class ReplaceTransformation(object):
    """
    Replaces a numbered line in a given file with a provided snippet.
    """
    def __init__(self, line: FileLine, snippet: Snippet) -> None:
        self.__line = line
        self.__snippet = snippet


class AppendTransformation(object):
    """
    Appends a given snippet to a specific line in a given file.
    """
    def __init__(self, line: FileLine, snippet: Snippet) -> None:
        self.__line = line
        self.__snippet = snippet


class TransformationDatabase(object):
    """
    Used to represent the space of all atomic program transformations.
    """
    @staticmethod
    def generate(bug: Bug,
                 pool: DonorPool,
                 lines: List[FileLine]) -> None:
        transformations = []
        for line in lines:
            # deletion
            transformations.append(DeleteTransformation(line))

            # replace and append
            for snippet in pool:
                transformations.append(ReplaceTransformation(line, snippet))
                transformations.append(AppendTransformation(line, snippet))
        return TransformationDatabase(transformations)

    def __init__(self, transformations: List[Transformation]):
        self.__transformations = transformations[:]
