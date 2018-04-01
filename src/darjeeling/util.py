from typing import List


def get_lines(fn: str) -> List[str]:
    """
    Attempts to return a list of all the lines in a given source code file.
    """
    # try to decode the file using the default encoding (should be utf-8)
    try:
        with open(fn, 'r') as f:
            return [l.rstrip('\n') for l in f]
    except UnicodeDecodeError:
        pass

    # let's try to decode the using latin-1 encoding
    with open(fn, 'r', encoding='latin-1') as f:
        return [l.rstrip('\n') for l in f]
