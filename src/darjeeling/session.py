# -*- coding: utf-8 -*-
from typing import List
import os
import asyncio
import logging

import attr

from .candidate import Candidate
from .searcher import Searcher
from .problem import Problem

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)


@attr.s
class Session:
    """Used to manage and inspect an interactive repair session."""
    dir_patches = attr.ib(type=str)
    searcher = attr.ib(type=Searcher)
    terminate_early = attr.ib(type=bool, default=True)
    _patches = attr.ib(type=List[Candidate], factory=list)

    @property
    def problem(self) -> Problem:
        """The repair problem that is being solved in this session."""
        return self._searcher.problem

    def run(self) -> None:
        logger.info("beginning search process...")
        if self.terminate_early:
            try:
                self._patches.append(next(self.searcher.__iter__()))
            except StopIteration:
                pass
        else:
            self._patches = list(self.searcher)
        if not self._patches:
            logger.info("failed to find a patch")

    def close(self) -> None:
        """Closes the session."""
        # wait for threads to finish gracefully before exiting
        self.searcher.close()

        # report stats
        num_test_evals = self.searcher.num_test_evals
        num_candidate_evals = self.searcher.num_candidate_evals
        time_running_mins = self.searcher.time_running.seconds / 60

        logger.info("found %d plausible patches", len(self._patches))
        logger.info("time taken: %.2f minutes", time_running_mins)
        logger.info("# test evaluations: %d", self.searcher.num_test_evals)
        logger.info("# candidate evaluations: %d",
                    self.searcher.num_candidate_evals)

    def pause(self) -> None:
        """Pauses the session."""
        raise NotImplementedError

    def _save_patches_to_disk(self) -> None:
        os.makedirs(self.dir_patches, exist_ok=True)
        for i, patch in enumerate(self._patches):
            diff = str(patch.to_diff(self.problem))
            fn_patch = os.path.join(self.dir_patches, '{}.diff'.format(i))
            logger.debug("writing patch to %s", fn_patch)
            try:
                with open(fn_patch, 'w') as f:
                    f.write(diff)
            except Exception:
                logger.exception("failed to write patch: %s", fn_patch)
                raise
            logger.debug("wrote patch to %s", fn_patch)
