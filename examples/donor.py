#!/usr/bin/env python
import bugzoo
from darjeeling.donor import DonorPool

if __name__ == '__main__':
    bz = bugzoo.BugZoo()
    bug_id = "ardudemo:ardupilot:overflow"
    bug = bz.bugs[bug_id]

    pool = DonorPool.from_file(bug, "APMrover2/commands_logic.cpp")
    for (i, snippet) in enumerate(pool, 1):
        print("{}: {}".format(i, snippet.content))
