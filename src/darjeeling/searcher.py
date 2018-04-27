from typing import Iterable, Iterator, Optional, List
from timeit import default_timer as timer
import logging
import datetime
import threading
import time
import signal

import bugzoo

from .candidate import Candidate
from .problem import Problem
from .outcome import OutcomeManager


__all__ = ['Searcher']


class Shutdown(Exception):
    pass


class Searcher(object):
    def __init__(self,
                 bugzoo: bugzoo.BugZoo,
                 problem: Problem,
                 candidates: Iterable[Candidate],
                 *,
                 threads: int = 1,
                 time_limit: Optional[datetime.timedelta] = None,
                 logger: Optional[logging.Logger] = None
                 ) -> None:
        """
        Constructs a new searcher for a given source of candidate patches.

        Parameters:
            bugzoo: a connection to the BugZoo server that should be used to
                evaluate candidate patches.
            problem: a description of the problem.
            candidates: a source of candidate patches.
            threads: the number of threads that should be made available to
                the search process.
            time_limit: an optional limit on the amount of time given to the
                searcher.
            logger: the logger that should be used.
        """
        assert time_limit is None or time_limit > datetime.timedelta(), \
            "if specified, time limit should be greater than zero."

        self.__bugzoo = bugzoo
        self.__problem = problem
        self.__candidates = candidates
        self.__time_limit = time_limit
        self.__num_threads = threads
        self.__outcomes = OutcomeManager()

        self.__logger = \
            problem.logger.getChild('search') if logger is None else logger
        self.logger.info("Constructed searcher")

        # records the time at which the current iteration begun
        self.__time_iteration_begun = None # type: Optional[float]

        self.__lock_candidates = threading.Lock() # type: threading.Lock
        self.__counter_candidates = 0
        self.__counter_tests = 0
        self.__exhausted_candidates = False
        self.__time_running = datetime.timedelta()
        self.__error_occurred = False
        self.__found_patches = [] # type: List[Candidate]

    @property
    def outcomes(self) -> OutcomeManager:
        """
        Provides a log of the outcomes of candidate patch build attempts and
        test executions.
        """
        return self.__outcomes

    @property
    def logger(self) -> logging.Logger:
        """
        Used to record logging information for the search.
        """
        return self.__logger

    @property
    def paused(self) -> bool:
        """
        Indicates whether this searcher is paused.
        """
        return (self.__found_patches != []) or self.exhausted

    @property
    def exhausted(self) -> bool:
        """
        Indicates whether or not the resources available to this searcher have
        been exhausted.
        """
        if self.__error_occurred:
            return True
        if self.__exhausted_candidates:
            return True
        if self.__time_limit is None:
            return False
        if self.time_running > self.time_limit:
            return True
        return False

    @property
    def num_test_evals(self) -> int:
        """
        The number of test case evaluations that have been performed during
        this search process.
        """
        return self.__counter_tests

    @property
    def num_candidate_evals(self) -> int:
        """
        The number of candidate patches that have been evaluated over the
        course of this search process.
        """
        return self.__counter_candidates

    @property
    def time_limit(self) -> Optional[datetime.timedelta]:
        """
        An optional limit on the length of time that may be spent searching
        for patches.
        """
        return self.__time_limit

    @property
    def time_running(self) -> datetime.timedelta:
        """
        The amount of time that has been spent searching for patches.
        """
        time_now = timer()
        duration_secs = time_now - self.__time_iteration_begun
        duration_iteration = datetime.timedelta(seconds=duration_secs) # type: datetime.timedelta
        duration_total = self.__time_running + duration_iteration
        # DEBUG
        duration_mins = duration_iteration.seconds / 60
        self.logger.debug("time running: {:.2f} minutes".format(duration_mins))
        return duration_total

    def __iter__(self) -> Iterator[Candidate]:
        return self

    def __next__(self) -> Candidate:
        """
        Searches for the next acceptable patch.

        Returns:
            the next patch that passes all tests.

        Raises:
            StopIteration: if the search space or available resources have
                been exhausted.
        """
        # if we have patches in the buffer, return those.
        if self.__found_patches:
            return self.__found_patches.pop()

        threads = [] # type: List[threading.Thread]

        # setup signal handlers to ensure that threads are cleanly killed
        # causes a Shutdown exception to be thrown in the search loop below
        self.logger.debug("Attaching signal handlers")
        def shutdown_handler(signum, frame):
            raise Shutdown
        original_handler_sigint = signal.getsignal(signal.SIGINT)
        original_handler_sigterm = signal.getsignal(signal.SIGTERM)
        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)
        self.logger.debug("Attached signal handlers")

        self.__time_iteration_begun = timer()

        # TODO there's a bit of a bug: any patches that were read from the
        #   generator by the worker and were still stored in its
        #   `candidate` variable will be discarded. fixable by adding a
        #   buffer to `_try_next`.
        try:
            def worker(searcher: 'Searcher') -> None:
                while True:
                    if not searcher._try_next():
                        break

            for _ in range(self.__num_threads):
                t = threading.Thread(target=worker, args=(self,))
                threads.append(t)
                t.start()

            for t in threads:
                t.join()
        except Shutdown:
            self.logger.info("Reached time limit without finding repair. Terminating search.")
            self.__error_occurred = True
        except Exception as e:
            self.__error_occurred = True
        finally:
            for t in threads:
                t.join()
            signal.signal(signal.SIGINT, original_handler_sigint)
            signal.signal(signal.SIGTERM, original_handler_sigterm)

        duration_iteration = timer() - self.__time_iteration_begun
        self.__time_running += datetime.timedelta(seconds=duration_iteration)

        # if we have a patch, return it
        if self.__found_patches:
            return self.__found_patches.pop()

        # if not, we're done
        raise StopIteration

    def _try_next(self) -> bool:
        """
        Evaluates the next candidate patch.

        Returns:
            a boolean indicating whether the calling thread should continue to
            evaluate candidate patches.
        """
        if self.paused:
            return False

        self.__lock_candidates.acquire()
        try:
            candidate = next(self.__candidates) # type: ignore
        except StopIteration:
            self.__logger.info("All candidate patches have been exhausted.")
            self.__exhausted_candidates = True
            return False
        finally:
            self.__lock_candidates.release()

        # TODO improve log format
        # create a logger for this particular candidate patch evaluation
        # logger = self.logger.getChild(str(candidate))
        logger = self.logger

        self.__counter_candidates += 1
        bz = self.__bugzoo
        container = bz.containers.provision(self.__problem.bug)
        try:
            patch = candidate.diff(self.__problem)
            diff = candidate.diff(self.__problem)
            logger.info("Evaluating: %s\n%s\n", candidate, diff)
            bz.containers.patch(container, patch)

            # ensure that the patch compiles
            outcome_compilation = bz.containers.compile(container)
            logger.debug("Compilation outcome for %s:\n%s",
                         candidate,
                         outcome_compilation.response.output)
            self.outcomes.record_build(candidate, outcome_compilation)
            if not outcome_compilation.successful:
                logger.info("Failed to compile: %s", candidate)
                return True

            # for now, execute all tests in no particular order
            # TODO perform test ordering
            for test in self.__problem.tests:
                cmd = self.__problem.bug.harness.command(test)[0]
                logger.info("Executing test: %s (%s)", test.name, candidate)
                self.__counter_tests += 1
                outcome = bz.containers.execute(container, test)
                logger.debug("* test outcome: %s (%s) [retcode=%d]\n$ %s\n%s",
                             test.name,
                             candidate,
                             outcome.response.code,
                             cmd,
                             outcome.response.output)
                self.outcomes.record_test(candidate, test.name, outcome)
                if not outcome.passed:
                    logger.info("* test failed: %s (%s)", test.name, candidate)
                    return True
                logger.info("* test passed: %s (%s)", test.name, candidate)

            # if we've found a repair, pause the search
            self.__found_patches.append(candidate)

            # report the patch
            logger.info("FOUND A REPAIR: %s", candidate)

            return True

        # TODO ensure a bool is returned when an exception occurs
        finally:
            logger.info("Evaluated: %s", candidate)
            if container:
                del bz.containers[container.uid]
