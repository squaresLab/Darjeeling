class FileCharRange(object):
    def __init__(self,
                 start: FileChar,
                 stop: FileChar
                 ) -> None:
        assert start.filename == stop.filename

    @property
    def filename(self) -> str:
        """
        The name of the file that this character range belongs to.
        """
        return self.start.filename

    @property
    def start(self) -> FileChar:
        """
        The beginning of this character range.
        """
        return self.__start

    @property
    def stop(self) -> FileChar:
        """
        The end (inclusive) of this character range.
        """
        return self.__stop
