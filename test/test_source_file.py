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
    char_range = FileCharRange(FileChar("test.txt", 12),
                               FileChar("test.txt", 19))
    f_orig = SourceFile("test.txt", contents)
    assert f_orig[char_range] == "example"
