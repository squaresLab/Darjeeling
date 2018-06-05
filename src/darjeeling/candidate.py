from typing import List, Iterator, Dict, FrozenSet

import attr
from bugzoo.core.patch import Patch

from .problem import Problem
from .transformation import Transformation, \
                            DeleteTransformation, \
                            ReplaceTransformation, \
                            AppendTransformation


@attr.s(frozen=True)
class Candidate(object):
    """
    Represents a candidate repair as a set of atomic program transformations.
    """
    transformations = attr.ib(type=FrozenSet[Transformation],
                              converter=frozenset)

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

        # FIXME this is stupid
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
