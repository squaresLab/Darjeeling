from .bindings import Binding, BindingsGenerator


class TransformationSchema(object):
    def __init__(self, matcher: str, rewriter: str) -> None:
        self.__matcher = matcher
        self.__rewriter = rewriter

    @property
    def matcher(self) -> str:
        """
        The matching pattern used by this schema.
        """
        return self.__matcher

    # TODO: we need to know free variables that should be supplied by the donor
    #   code pool or some other source
    # if there are no variables in the rewriter, we can perform good
    # old-fashioned string replacement (without the need to make another
    # API call)
    @property
    def rewriter(self) -> str:
        """
        The rewriting pattern used by this schema.
        """
        return self.__rewriter

    def completions(self, List[Binding]) -> List[Transformation]:
        """
        Returns a list of all completions of this transformation schema at
        a given binding.
        """
        raise NotImplementedError


class TransformationGenerator(object):
    """

    """
    def __init__(self,
                 bindings: BindingsGenerator
                 ) -> None:
        self.__buffer = []
        self.__bindings = bindings

    def __iter__(self) -> Iterator[Transformation]:
        return self

    def __next__(self) -> Transformation:
        # attempt to empty the buffer before computing more transformations
        if self.__buffer:
            return self.__buffer.pop(0)

        # find all completions for the next binding
        try:
            binding = next(self.__bindings)
        # sort of redundant?
        except StopIteration:
            raise StopIteration

        schema = binding.schema # TODO fetch schema
        transformations_for_binding = schema.completions(binding)
        return self.__next__()
