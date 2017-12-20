class Line(object):
    """
    Represents the nth line within a given file.
    """
    def __init__(self,
                 filename: str,
                 num: int
                 ) -> None:
        assert num > 0
        self.__filename = filename
        self.__num = num

    @property
    def filename(self) -> str:
        """
        The name of the file to which this line belongs.
        """
        return self.__filename

    @property
    def num(self) -> int:
        """
        The one-indexed number of this line.
        """
        return self.__num
