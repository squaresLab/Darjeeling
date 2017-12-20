from typing import List, Iterator


class Candidate(object):
    """
    Represents a candidate repair as a set of atomic program transformations.
    """
    def __init__(self,
                 transformations: List[Transformation]
                 ) -> None:
        self.__transformations = frozenset(transformations)


    @property
    def transformations(self) -> Iterator[Transformation]:
        """
        The transformations that comprise this repair.
        """
        for t in self.__transformations:
            yield t

    @property
    def diff(self) -> str:
        """
        Returns a plaintext diff for this repair.
        """
        raise NotImplementedError
