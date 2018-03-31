from typing import Iterator, List


class Binding(object):
    def __init__(self,
                 target: FileCharRange,
                 schema: TransformationSchema
                 ) -> None:
        self.__target =
        self.__schema = schema
        self.__environment = 

    @property
    def schema(self) -> TransformationSchema:
        """
        The transformation schema used to generate this binding.
        """
        return self.__schema


class BindingGenerator(object):
    """
    Lazily finds all bindings for a specified set of transformation schemas at a
    given set of transformation targets. (I.e., it finds all transformation
    targets where transformation schemas may be applied.)
    """
    def __init__(self,
                 schemas: List[TransformationSchema],
                 targets: List[FileCharRange]
                 ) -> None:
        assert schemas != []
        assert targets != []

        self.__schemas = reversed(schemas)
        self.__remaining_targets = reversed(targets)

        self.__current_target = None
        self.__current_schemas = []

    def __iter__(self) -> Iterator[Binding]:
        return self

    def __next__(self) -> Binding:
        # empty the contents of the buffer before computing more bindings
        if self.__buffer:
            return self.__buffer.pop(0)

        # move onto the next transformation target once we've attempted to find
        # all bindings of the transformation schemas at the current target.
        if not self.__current_schemas:
            if not self.__remaining_targets:
                raise StopIteration

            self.__current_target = self.__remaining_targets.pop()
            self.__current_schemas = self.__schemas.copy()

        # find all bindings for the next schema at the current target
        # store them in the buffer
        # TODO API call to Rooibos
        schema = self.__current_schemas.pop()
        self.__buffer = presto.matches(self.__current_target, schema.match)
        # TODO apply filtering to bindings

        return self.__next__()
