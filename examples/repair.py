#!/usr/bin/env python
import bugzoo
from darjeeling.problem import Problem
from darjeeling.repair import repair


if __name__ == '__main__':
    bz = bugzoo.BugZoo()
    bug_id = "ardudemo:ardupilot:overflow"
    in_files = ['APMrover2/commands_logic.cpp']
    problem = Problem(bz.bugs[bug_id], in_files)
    metric = bugzoo.localization.suspiciousness.tarantula

    repair(problem, metric)
