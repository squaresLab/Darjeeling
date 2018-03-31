from typing import Iterable, Iterator
from timeit import default_timer as timer
import datetime

from .candidate import Candidate
from .problem import Problem


__ALL__ = ['Searcher']


class Worker(threading.Thread):
    def __init__(self, searcher: 'Searcher') -> None:
        super().__init__()
        self.daemon = True
        self.__searcher = searcher
        self.start()

    # TODO: collapse into a closure
    def run(self) -> None:
        while True:
            if not self.__searcher._try_next():
                break


class Searcher(object):
    def __init__(self,
                 problem: Problem,
                 candidates: Iterable[Candidate],
                 *,
                 threads: int = 1,
                 time_limit: Optional[timedelta] = None
                 ) -> None:
        """
        Constructs a new searcher for a given source of candidate patches.

        Parameters:
            problem: a description of the problem.
            candidates: a source of candidate patches.
            threads: the number of threads that should be made available to
                the search process.
            time_limit: an optional limit on the amount of time given to the
                searcher.
        """
        assert time_limit is None or time_limit > 0, \
            "if specified, time limit should be greater than zero."

        self.__problem = problem
        self.__candidates = candidates
        self.__time_running = datetime.timedelta()
        self.__time_limit = time_limita
        self.__num_threads = threads

        # records the time at which the current iteration begun
        self.__time_iteration_begun = None

        self.__counter_candidates = 0
        self.__counter_tests = 0

    @property
    def running(self) -> bool:
        """
        Indicates whether this searcher is currently searching for patches.
        """
        return self.__running

    @property
    def exhausted(self) -> bool:
        """
        Indicates whether or not the resources available to this searcher have
        been exhausted.
        """
        if self.__time_limit is None:
            return False

        return self.time_running > self.time_limit

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
        duration_iteration = timer() - self.__time_start_iteration
        return self.__time_running + duration_iteration

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
        self.__time_iteration_begun = timer()
        try:
            workers = [Worker(self) for _ in range(self.__num_threads)]

            # block until time has expired or we've found another repair
            pass

            self.__paused = True

        finally:
            # TODO this is bad -- use while instead
            # TODO there's a bit of a bug: any patches that were read from the
            #   generator by the worker and were still stored in its
            #   `candidate` variable will be discarded
            for worker in workers:
                worker.join()

            duration_iteration = timer() - self.__time_start_iteration
            self.__time_running += duration_iteration

    def _try_next(self) -> bool:
        """
        Evaluates the next candidate patch.

        Returns:
            a boolean indicating whether the calling thread should continue to
            evaluate candidate patches.
        """
        # TODO have we run out of precious resources?

        # TODO: this MUST be protected
        try:
            candidate = next(self.__candidates)
        except StopIteration:
            print("exhausted all candidate patches!")
            return False

        print("Evaluating: {}".format(candidate))
        self.__counter_candidates += 1
        bz = self.__bugzoo
        container = bz.containers.provision(self.__problem.bug)
        try:
            patch = candidate.diff(self.__problem)
            bz.containers.patch(container, patch)

            # ensure that the patch compiles
            if not bz.containers.compile(container).successful:
                print("Failed to compile: {}".format(candidate))
                return True

            # for now, execute all tests in no particular order
            # TODO perform test ordering
            for test in self.problem.tests:
                print("Executing test: {} ({})".format(test.name, candidate))
                self.__counter_tests += 1
                outcome = bz.containers.execute(container, test)
                if not outcome.passed:
                    print("Failed test: {} ({})".format(test.name, candidate))
                    return True
                print("Passed test: {} ({})".format(test.name, candidate))

            # if we've found a repair, pause the search
            self.__repairs.append(candidate)
            diff = candidate.diff(self.problem)

            # how long did it take to find a repair?
            time_repair = self.time_running.seconds / 60.0
            print("FOUND REPAIR [{:.2f} minutes]: {}\n{}\n{}\n{}".format(time_repair, candidate,
                                                        ("=" * 80),
                                                        diff,
                                                        ("="*80)))
            return True
        finally:
            print("Evaluated: {}".format(candidate))
            if container:
                del bz.containers[container.uid]
