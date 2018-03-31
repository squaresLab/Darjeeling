from bugzoo.core.fileline import FileLine


def ends_with_semi_colon(line: FileLine, contents: str) -> bool:
    """
    Returns `True` if a given line ends with a semi-colon.
    """
    return contents.rstrip().endswith(';')
