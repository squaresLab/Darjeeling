#!/usr/bin/env python
import bugzoo
import bugzoo.localization
import darjeeling
import darjeeling.repair
import datetime


def main():
    bz = bugzoo.BugZoo()
    bug = bz.bugs["tse2012:zune"]
    bz.bugs.build(bug, force=True)

    files = ['zune.c']
    # files = ['atris_comb.c']
    problem = darjeeling.problem.Problem(bz, bug,
                                         in_files=files)

    print("\n[LINES]\n")
    for line in problem.lines:
        fn = line.filename
        src = problem.source(fn)
        char_range = src.line_to_char_range(line)
        content = src[char_range]
        print("{} / {}: '{}'".format(line, char_range, content))
    print("[\LINES]\n")

    print("\n[SNIPPETS]")
    for (i, snippet) in enumerate(problem.snippets):
        print("{}: {}".format(i, snippet))
    print("[\SNIPPETS]\n")

    time_limit = datetime.timedelta(minutes=15)

    patches, report = darjeeling.repair.repair(bz,
                                               problem,
                                               threads=10,
                                               seed=0,
                                               time_limit=time_limit)


if __name__ == '__main__':
    main()
