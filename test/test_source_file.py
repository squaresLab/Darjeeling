import pytest
from bugzoo.core.filechar import FileCharRange, FileChar
from darjeeling.source import SourceFile


contents = """
This is an example source code file.
It
has
a
few
lines
that we can edit.

Here's another line!
""".strip()


def test_access():
    char_range = FileCharRange(FileChar("test.txt", 11),
                               FileChar("test.txt", 17))
    f_orig = SourceFile("test.txt", contents)
    assert contents[11:18] == "example"
    assert f_orig[char_range] == "example"


def test_delete():
    char_range = FileCharRange(FileChar("test.txt", 11),
                               FileChar("test.txt", 17))
    f_orig = SourceFile("test.txt", contents)

    f_mod = f_orig.delete(char_range)
    assert str(f_mod) == contents[0:11] + contents[18:]
