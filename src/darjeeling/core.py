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
    def filename(self):
        """
        The name of the file to which this line belongs.
        """
        return self.__filename

    @property
    def num(self):
        """
        The one-indexed number of this line.
        """
        return self.__num
