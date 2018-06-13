#!/usr/bin/env python
import logging
import datetime

import rooibos
import bugzoo
import bugzoo.localization
import darjeeling
import darjeeling.repair
from darjeeling.snippet import SnippetDatabase


def main():
    bz = bugzoo.BugZoo()
    bug = bz.bugs["tse2012:zune"]
    bz.bugs.build(bug, force=True)

    files = ['zune.c']
    # files = ['atris_comb.c']

    with rooibos.ephemeral_server() as client_rooibos:
        coverage = bz.bugs.coverage(bug)
        problem = darjeeling.problem.Problem(bz,
                                             bug,
                                             coverage,
                                             client_rooibos=client_rooibos)
        snippets = SnippetDatabase.from_problem(problem)
        # FIXME add filtering
        print("\n[SNIPPETS]")
        for (i, snippet) in enumerate(snippets):
            print("{}: {}".format(i, snippet))
        print("[\SNIPPETS]\n")

        time_limit = datetime.timedelta(minutes=15)

        # let's setup logging
        log_to_stdout = logging.StreamHandler()
        log_to_stdout.setLevel(logging.DEBUG)
        logging.getLogger('darjeeling').addHandler(log_to_stdout)

        patches, report = darjeeling.repair.repair(bz,
                                                   problem,
                                                   threads=10,
                                                   seed=0,
                                                   time_limit=time_limit)


if __name__ == '__main__':
    main()
