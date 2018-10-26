import pytest
from bugzoo.core.filechar import FileCharRange, FileChar

from darjeeling.localization import Localization
from darjeeling.core import FileLine
import darjeeling.exceptions

l = FileLine.from_string


def test_empty_throws_exception():
    with pytest.raises(darjeeling.exceptions.NoImplicatedLines):
        Localization({})


def test_contains():
    loc = Localization.from_dict({
        'foo.c:1': 1.0,
        'foo.c:2': 1.0,
        'foo.c:3': 1.0
    })
    assert l('foo.c:1') in loc
    assert l('foo.c:2') in loc
    assert l('foo.c:3') in loc
    assert l('foo.c:4') not in loc
    assert l('bar.c:1') not in loc


def test_get():
    loc = Localization.from_dict({
        'foo.c:1': 1.0,
        'foo.c:2': 0.5,
        'foo.c:3': 0.1
    })
    assert loc[l('foo.c:1')] == 1.0
    assert loc[l('foo.c:2')] == 0.5
    assert loc[l('foo.c:3')] == 0.1
    assert loc[l('foo.c:4')] == 0.0
    assert loc[l('bar.c:1')] == 0.0
