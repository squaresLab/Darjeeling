import pytest
from bugzoo.core.filechar import FileCharRange, FileChar

from darjeeling.localization import Localization
from darjeeling.core import FileLine
import darjeeling.exceptions

l = FileLine.from_string


def test_empty_throws_exception():
    with pytest.raises(darjeeling.exceptions.NoImplicatedLines):
        Localization({})


def test_to_and_from_dict():
    loc = Localization({
        l('foo.c:1'): 1.0,
        l('foo.c:2'): 0.1,
        l('foo.c:3'): 0.5,
        l('bar.c:9'): 0.1
    })

    dict_expected = {
        'foo.c:1': 1.0,
        'foo.c:2': 0.1,
        'foo.c:3': 0.5,
        'bar.c:9': 0.1
    }

    assert loc.to_dict() == dict_expected
    assert Localization.from_dict(dict_expected) == loc


def test_iter():
    loc = Localization.from_dict({
        'foo.c:1': 1.0,
        'foo.c:2': 1.0,
        'foo.c:3': 1.0
    })

    lines_expected = \
        {l('foo.c:1'), l('foo.c:2'), l('foo.c:3')}
    lines_actual = set(loc)

    assert lines_expected == lines_actual


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
