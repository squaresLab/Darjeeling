__all__ = ['GeneticSearcher']

from typing import Iterator, List, Optional, Dict, Any, Union
import concurrent.futures
import logging
import random
import datetime

import bugzoo
from bugzoo.client import Client as BugZooClient

from .base import Searcher
from ..candidate import Candidate
from ..transformation import Transformation
from ..problem import Problem
from ..outcome import CandidateOutcome

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

Population = List[Candidate]


class GeneticSearcher(Searcher):
    @staticmethod
    def from_dict(d: Dict[str, Any],
                  problem: Problem,
                  transformations: List[Transformation],
                  *,
                  threads: int = 1,
                  candidate_limit: Optional[int] = None,
                  time_limit: Optional[datetime.timedelta] = None
                  ) -> 'GeneticSearcher':
        sample_size = \
            d.get('test-sample-size')  # type: Optional[Union[int, float]]
        num_generations = d.get('generations', 10)  # type: int
        population_size = d.get('population', 40)  # type: int
        rate_mutation = d.get('mutation-rate', 1.0)  # type: float
        rate_crossover = d.get('crossover-rate', 1.0)  # type: float
        tournament_size = d.get('tournament-size', 2)  # type: int
        return GeneticSearcher(problem.bugzoo,
                               problem,
                               transformations,
                               threads=threads,
                               candidate_limit=candidate_limit,
                               num_generations=num_generations,
                               population_size=population_size,
                               rate_crossover=rate_crossover,
                               rate_mutation=rate_mutation,
                               tournament_size=tournament_size,
                               test_sample_size=sample_size,
                               time_limit=time_limit)

    def __init__(self,
                 bugzoo: bugzoo.BugZoo,
                 problem: Problem,
                 transformations: List[Transformation],
                 *,
                 population_size: int = 40,
                 num_generations: int = 10,
                 rate_crossover: float = 1.0,
                 rate_mutation: float = 1.0,
                 tournament_size: int = 2,
                 threads: int = 1,
                 time_limit: Optional[datetime.timedelta] = None,
                 candidate_limit: Optional[int] = None,
                 test_sample_size: Optional[Union[int, float]] = None
                 ) -> None:
        self.__population_size = population_size
        self.__num_generations = num_generations
        self.__rate_crossover = rate_crossover
        self.__rate_mutation = rate_mutation
        self.__tournament_size = tournament_size
        self.__transformations = transformations

        m = ("using GA settings:\n"
             "  * num. generations: %d\n"
             "  * population size: %d\n"
             "  * tournament size: %d\n"
             "  * mutation rate: %.2f\n"
             "  * crossover rate: %.2f")
        logger.info(m,
                    self.__num_generations,
                    self.__population_size,
                    self.__tournament_size,
                    self.__rate_mutation,
                    self.__rate_crossover)

        super().__init__(bugzoo,
                         problem,
                         threads=threads,
                         time_limit=time_limit,
                         test_sample_size=test_sample_size,
                         candidate_limit=candidate_limit,
                         terminate_early=False)

    @property
    def population_size(self) -> int:
        return self.__population_size

    @property
    def num_generations(self) -> int:
        return self.__num_generations

    @property
    def rate_crossover(self) -> float:
        return self.__rate_crossover

    @property
    def rate_mutation(self) -> float:
        return self.__rate_mutation

    @property
    def tournament_size(self) -> int:
        return self.__tournament_size

    def initial(self) -> Population:
        """
        Generates an initial population according to this strategy.
        """
        pop = []
        for _ in range(self.population_size):
            pop.append(Candidate([]))
        return self.mutate(pop)

    def choose_transformation(self) -> Transformation:
        # FIXME for now, just pick one at random
        return random.choice(self.__transformations)

    def fitness(self,
                population: Population,
                outcomes: Dict[Candidate, CandidateOutcome]
                ) -> Dict[Candidate, float]:
        """
        Computes the fitness of each individual within a population.
        """
        logger.debug("computing population fitness...")
        f = {}  # type: Dict[Candidate, float]
        for ind in population:
            outcome = outcomes[ind]
            if not outcome.build.successful:
                f[ind] = 0.0
            else:
                # FIXME maybe we don't need to execute the test?
                f[ind] = sum(1.0 for n in outcome.tests if outcome.tests[n].successful)
        logger.info("computed fitness:\n%s",
                     '\n'.join(['  {}: {}'.format(ind, f[ind]) for ind in f]))
        return f

    def select(self,
               pop: Population,
               outcomes: Dict[Candidate, CandidateOutcome]
               ) -> Population:
        """
        Selects N individuals from the population to survive into the
        next generation.
        """
        survivors = []  # type: Population
        ind_to_fitness = self.fitness(pop, outcomes)
        for _ in range(self.population_size):
            participants = random.sample(pop, self.tournament_size)
            winner = max(participants, key=ind_to_fitness.__getitem__)
            survivors.append(winner)
        return survivors

    def mutate(self, pop: Population) -> Population:
        offspring = []
        for ind in pop:
            child = ind
            if random.random() <= self.rate_mutation:
                mutation = self.choose_transformation()
                child = Candidate(child.transformations + (mutation,))
            offspring.append(child)
        return offspring

    def crossover(self, pop: Population) -> Population:
        def one_point_crossover(px: Candidate,
                                py: Candidate
                                ) -> List[Candidate]:
            tx = list(px.transformations)
            ty = list(py.transformations)

            lx = random.randint(0, len(tx))
            ly = random.randint(0, len(ty))

            a, b = tx[:lx], tx[lx:]
            c, d = ty[:ly], ty[ly:]

            children = [Candidate(a + d), Candidate(c + b)]  # type: ignore
            return children

        offspring = []  # type: List[Candidate]
        random.shuffle(pop)
        k = 2
        for i in range(0, len(pop), k):
            parents = pop[i:i+k]
            offspring += parents
            if len(parents) == k and random.random() <= self.rate_crossover:
                offspring += one_point_crossover(*parents)
        return offspring

    def run(self) -> Iterator[Candidate]:
        outcomes = {}  # type: Dict[Candidate, CandidateOutcome]
        logger.info("generating initial population...")
        pop = self.initial()
        logger.info("generated initial population")

        logger.info("evaluating initial population...")
        yield from self.evaluate_all(pop, outcomes)
        logger.info("evaluated initial population")

        logger.info("selecting survivors...")
        pop = self.select(pop, outcomes)  # should this happen at the start?
        logger.info("selected survivors")

        for g in range(0, self.num_generations + 1):
            logger.info("starting generation %d...", g)
            pop = self.crossover(pop)
            pop = self.mutate(pop)
            logger.info("evaluating candidate patches...")
            outcomes = {}
            yield from self.evaluate_all(pop, outcomes)
            logger.info("evaluated candidate patches")
            pop = self.select(pop, outcomes)
