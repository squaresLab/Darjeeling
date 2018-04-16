from typing import List, Iterator, Dict

from bugzoo.core.patch import Patch

from darjeeling.transformation import Transformation, \
                                      DeleteTransformation, \
                                      ReplaceTransformation, \
                                      AppendTransformation
from darjeeling.problem import Problem


# class RawPatchCandidate(object):
#     def __init__(self, patch: Patch) -> None:
#         self.__patch = patch
# 
#     def __str__(self) -> str:
#         return str(self.__patch)
# 
#     def diff(self, problem: Problem) -> Patch:

class Candidate(object):
    """
    Represents a candidate repair as a set of atomic program transformations.
    """
    def __init__(self,
                 transformations: List[Transformation]
                 ) -> None:
        self.__transformations = frozenset(transformations)

    def __str__(self) -> str:
        transformations_s = \
            ', '.join([str(t) for t in self.transformations])
        return "<{}>".format(transformations_s)

    @property
    def transformations(self) -> Iterator[Transformation]:
        """
        The transformations that comprise this repair.
        """
        for t in self.__transformations:
            yield t

    def diff(self, problem: Problem) -> Patch:
        """
        Computes a plaintext diff for this repair.
        """
        # group transformations by file
        tf = {} # type: Dict[str, List[Transformation]]
        for t in self.transformations:
            fn = t.char_range.filename # type: ignore
            if fn not in tf:
                tf[fn] = []
            tf[fn].append(t)

        # order each group of transformations in descending order of
        # line number
        for group in tf.values():
            group.sort(key=lambda t: t.char_range.start.offset, reverse=True) # type: ignore

        # transform each group into a modified source code file
        transformed = problem.sources
        for (fn, transformations) in tf.items():
            for t in transformations:
                if isinstance(t, DeleteTransformation):
                    transformed = transformed.delete(t.char_range)
                elif isinstance(t, AppendTransformation):
                    transformed = transformed.insert(t.char_range.stop, str(t.snippet))
                elif isinstance(t, ReplaceTransformation):
                    transformed = transformed.replace(t.char_range, str(t.snippet))
                else:
                    raise Exception("unsupported transformation")

        # FIXME use SourceFileCollection.diff
        # compute a diff for each modified source code file
        diffs = []
        for fn in transformed:
            source_after = transformed[fn]
            source_before = problem.sources[fn]
            diffs.append(source_before.diff(source_after))

        # combine the diffs for each file into a single diff
        diff = '\n'.join(diffs)
        return Patch.from_unidiff(diff)
