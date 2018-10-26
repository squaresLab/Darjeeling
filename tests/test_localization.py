import pytest
from bugzoo.core.filechar import FileCharRange, FileChar

from darjeeling.localization import Localization
import darjeeling.exceptions


def test_empty_throws_exception():
    with pytest.raises(darjeeling.exceptions.NoImplicatedLines):
        Localization({})
