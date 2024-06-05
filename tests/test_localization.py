
import pytest

import darjeeling.exceptions
from darjeeling.core import FileLine
from darjeeling.localization import Localization

l = FileLine.from_string


def test_empty_throws_exception():
    with pytest.raises(darjeeling.exceptions.NoImplicatedLines):
        Localization({})


def test_eq():
    l1 = Localization({
        l("foo.c:1"): 1.0,
        l("foo.c:2"): 0.1,
        l("foo.c:3"): 0.5,
        l("bar.c:9"): 0.1,
    })
    l2 = Localization({
        l("foo.c:1"): 1.0,
        l("foo.c:2"): 0.1,
        l("foo.c:3"): 0.5,
        l("bar.c:9"): 0.1,
    })
    l3 = Localization({
        l("foo.c:2"): 0.1,
        l("foo.c:3"): 0.5,
    })

    assert l1 == l2
    assert l2 == l1
    assert l1 != l3
    assert l3 != l1
    assert l2 != l3
    assert l3 != l2


def test_to_and_from_dict():
    loc = Localization({
        l("foo.c:1"): 1.0,
        l("foo.c:2"): 0.1,
        l("foo.c:3"): 0.5,
        l("bar.c:9"): 0.1,
    })

    dict_expected = {
        "foo.c:1": 1.0,
        "foo.c:2": 0.1,
        "foo.c:3": 0.5,
        "bar.c:9": 0.1,
    }

    assert loc.to_dict() == dict_expected
    assert Localization.from_dict(dict_expected) == loc


def test_len():
    ld = Localization.from_dict
    loc = ld({"foo.c:1": 1.0})
    assert len(loc) == 1
    loc = ld({"foo.c:1": 1.0, "foo.c:2": 1.0})
    assert len(loc) == 2
    loc = ld({"foo.c:1": 1.0, "foo.c:2": 1.0, "bar.c:1": 1.0})
    assert len(loc) == 3


def test_files():
    loc = Localization.from_dict({
        "foo.c:1": 1.0,
        "foo.c:2": 1.0,
        "bar.c:1": 1.0,
    })
    assert set(loc.files) == {"foo.c", "bar.c"}


def test_iter():
    loc = Localization.from_dict({
        "foo.c:1": 1.0,
        "foo.c:2": 1.0,
        "foo.c:3": 1.0,
    })

    lines_expected = \
        {l("foo.c:1"), l("foo.c:2"), l("foo.c:3")}
    lines_actual = set(loc)

    assert lines_expected == lines_actual


def test_contains():
    loc = Localization.from_dict({
        "foo.c:1": 1.0,
        "foo.c:2": 1.0,
        "foo.c:3": 1.0,
    })
    assert l("foo.c:1") in loc
    assert l("foo.c:2") in loc
    assert l("foo.c:3") in loc
    assert l("foo.c:4") not in loc
    assert l("bar.c:1") not in loc


def test_get():
    loc = Localization.from_dict({
        "foo.c:1": 1.0,
        "foo.c:2": 0.5,
        "foo.c:3": 0.1,
    })
    assert loc[l("foo.c:1")] == 1.0
    assert loc[l("foo.c:2")] == 0.5
    assert loc[l("foo.c:3")] == 0.1
    assert loc[l("foo.c:4")] == 0.0
    assert loc[l("bar.c:1")] == 0.0


def test_without():
    l1 = Localization.from_dict({
        "foo.c:1": 1.0,
        "foo.c:2": 0.5,
        "foo.c:3": 0.1,
    })

    l2 = l1.without(l("foo.c:2"))
    assert l2 == \
        Localization.from_dict({
            "foo.c:1": 1.0,
            "foo.c:3": 0.1,
        })

    l3 = l2.without(l("foo.c:2"))
    assert l3 == \
        Localization.from_dict({
            "foo.c:1": 1.0,
            "foo.c:3": 0.1,
        })

    l4 = l3.without(l("foo.c:1"))
    assert l4 == \
        Localization.from_dict({
            "foo.c:3": 0.1,
        })

    with pytest.raises(darjeeling.exceptions.NoImplicatedLines):
        l4.without(l("foo.c:3"))


def test_exclude_files():
    loc = Localization.from_dict({
        "foo.c:1": 1.0,
        "foo.c:2": 1.0,
        "foo.c:3": 1.0,
        "bar.c:1": 1.0,
        "bar.c:2": 1.0,
        "woo.c:1": 1.0,
    })

    assert len(loc.exclude_files([])) == 6
    assert len(loc.exclude_files(["buzz.c"])) == 6
    assert len(loc.exclude_files(["foo.c"])) == 3
    assert len(loc.exclude_files(["bar.c"])) == 4
    assert len(loc.exclude_files(["woo.c"])) == 5
    assert len(loc.exclude_files(["bar.c", "woo.c"])) == 3
    assert len(loc.exclude_files(["bar.c", "foo.c"])) == 1


def test_restrict_to_lines():
    loc = Localization.from_dict({
        "foo.c:1": 1.0,
        "foo.c:2": 0.5,
        "foo.c:3": 0.1,
    })

    restricted_to = {l("foo.c:1"), l("foo.c:2")}
    assert set(loc.restrict_to_lines(restricted_to)) == restricted_to

    restricted_to = {l("foo.c:1"), l("foo.c:2"), l("bar.c:7")}
    assert set(loc.restrict_to_lines(restricted_to)) == {
            l("foo.c:1"), l("foo.c:2")}

    restricted_to = {l("foo.c:1")}
    assert set(loc.restrict_to_lines(restricted_to)) == restricted_to

    with pytest.raises(darjeeling.exceptions.NoImplicatedLines):
        loc.restrict_to_lines({})


def test_exclude_lines():
    def fl(lines: list[str]) -> set[FileLine]:
        return set(FileLine.from_string(l) for l in lines)

    def ld(lines: list[str]) -> Localization:
        return Localization({l: 1.0 for l in fl(lines)})

    loc = ld(["foo.c:1", "foo.c:2", "foo.c:3", "bar.c:1", "bar.c:2"])
    assert loc.exclude_lines(fl(["foo.c:1"])) == \
        ld(["foo.c:2", "foo.c:3", "bar.c:1", "bar.c:2"])

    assert loc == loc.exclude_lines([])

    assert loc.exclude_lines(fl(["foo.c:1", "bar.c:2"])) == \
        ld(["foo.c:2", "foo.c:3", "bar.c:1"])

    with pytest.raises(darjeeling.exceptions.NoImplicatedLines):
        loc.exclude_lines(fl(["foo.c:1", "foo.c:2", "foo.c:3", "bar.c:1", "bar.c:2"]))
