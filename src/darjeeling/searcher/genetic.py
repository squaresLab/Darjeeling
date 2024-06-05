__all__ = ("GeneticSearcher",)

import random
import typing
from collections.abc import Iterator
from typing import Any, Optional, Union

import attr
from loguru import logger

from ..candidate import Candidate
from ..outcome import CandidateOutcome
from ..resources import ResourceUsageTracker
from ..transformation import ProgramTransformations, Transformation
from .base import Searcher
from .config import SearcherConfig

if typing.TYPE_CHECKING:
    from ..problem import Problem

Population = list[Candidate]


@attr.s(frozen=True, slots=True)
class GeneticSearcherConfig(SearcherConfig):
    """A configuration for a genetic search."""
    NAME = "genetic"

    num_generations: int = attr.ib(default=10)
    population_size: int = attr.ib(default=40)
    rate_mutation: float = attr.ib(default=1.0)
    rate_crossover: float = attr.ib(default=1.0)
    tournament_size: int = attr.ib(default=2)
    sample_size: Optional[Union[int, float]] = attr.ib(default=None)

    @classmethod
    def from_dict(cls,
                  d: dict[str, Any],
                  dir_: Optional[str] = None,
                  ) -> "SearcherConfig":
        num_generations: int = d.get("generations", 10)
        population_size: int = d.get("population", 40)
        rate_mutation: float = d.get("mutation-rate", 1.0)
        rate_crossover: float = d.get("crossover-rate", 1.0)
        tournament_size: int = d.get("tournament-size", 2)
        sample_size: Optional[Union[int, float]] = d.get("test-sample-size")
        return GeneticSearcherConfig(num_generations=num_generations,
                                     population_size=population_size,
                                     rate_mutation=rate_mutation,
                                     rate_crossover=rate_crossover,
                                     tournament_size=tournament_size,
                                     sample_size=sample_size)

    def build(self,
              problem: "Problem",
              resources: ResourceUsageTracker,
              transformations: ProgramTransformations,
              *,
              threads: int = 1,
              run_redundant_tests: bool = False,
              ) -> Searcher:
        return GeneticSearcher(problem=problem,
                               resources=resources,
                               transformations=transformations,
                               threads=threads,
                               num_generations=self.num_generations,
                               population_size=self.population_size,
                               rate_crossover=self.rate_crossover,
                               rate_mutation=self.rate_mutation,
                               tournament_size=self.tournament_size,
                               test_sample_size=self.sample_size,
                               run_redundant_tests=run_redundant_tests)


class GeneticSearcher(Searcher):
    def __init__(self,
                 problem: "Problem",
                 resources: ResourceUsageTracker,
                 transformations: ProgramTransformations,
                 *,
                 population_size: int = 40,
                 num_generations: int = 10,
                 rate_crossover: float = 1.0,
                 rate_mutation: float = 1.0,
                 tournament_size: int = 2,
                 threads: int = 1,
                 run_redundant_tests: bool = True,
                 test_sample_size: Optional[Union[int, float]] = None,
                 ) -> None:
        self.__population_size = population_size
        self.__num_generations = num_generations
        self.__rate_crossover = rate_crossover
        self.__rate_mutation = rate_mutation
        self.__tournament_size = tournament_size
        self.__transformations = transformations

        logger.info("using GA settings:\n"
                    f"  * num. generations: {self.__num_generations}\n"
                    f"  * population size: {self.__population_size}\n"
                    f"  * tournament size: {self.__tournament_size}\n"
                    f"  * mutation rate: {self.__rate_mutation:.2f}\n"
                    f"  * crossover rate: {self.__rate_crossover:.2f}")

        super().__init__(problem=problem,
                         resources=resources,
                         threads=threads,
                         run_redundant_tests=run_redundant_tests,
                         test_sample_size=test_sample_size,
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
        """Generates an initial population according to this strategy."""
        pop = []
        for _ in range(self.population_size):
            pop.append(Candidate(self.problem, []))
        return self.mutate(pop)

    def choose_transformation(self) -> Transformation:
        # FIXME for now, just pick one at random
        return self.__transformations.choice()

    def fitness(
        self,
        population: Population,
        outcomes: dict[Candidate, CandidateOutcome],
    ) -> dict[Candidate, float]:
        """Computes the fitness of each individual within a population."""
        logger.debug("computing population fitness...")
        f: dict[Candidate, float] = {}
        for ind in population:
            outcome = outcomes[ind]
            if not outcome.build.successful:
                f[ind] = 0.0
            else:
                # FIXME maybe we don't need to execute the test?
                f[ind] = sum(1.0 for n in outcome.tests if outcome.tests[n].successful)
        logger.info("computed fitness:\n{}",
                    "\n".join(f"  {ind}: {f[ind]}" for ind in f))
        return f

    def select(self,
               pop: Population,
               outcomes: dict[Candidate, CandidateOutcome],
               ) -> Population:
        """Selects N individuals from the population to survive into the
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
        problem = self.problem
        offspring = []
        for ind in pop:
            child = ind
            if random.random() <= self.rate_mutation:
                mutation = self.choose_transformation()
                transformations = child.transformations + (mutation,)
                child = Candidate(problem, transformations)
            offspring.append(child)
        return offspring

    def crossover(self, pop: Population) -> Population:
        def one_point_crossover(px: Candidate,
                                py: Candidate,
                                ) -> list[Candidate]:
            problem = self.problem
            tx = list(px.transformations)
            ty = list(py.transformations)

            lx = random.randint(0, len(tx))
            ly = random.randint(0, len(ty))

            a, b = tx[:lx], tx[lx:]
            c, d = ty[:ly], ty[ly:]

            children = [Candidate(problem, a + d), Candidate(problem, c + b)]
            return children

        offspring: list[Candidate] = []
        random.shuffle(pop)
        k = 2
        for i in range(0, len(pop), k):
            parents = pop[i:i + k]
            offspring += parents
            if len(parents) == k and random.random() <= self.rate_crossover:
                offspring += one_point_crossover(*parents)
        return offspring

    def run(self) -> Iterator[Candidate]:
        outcomes: dict[Candidate, CandidateOutcome] = {}
        logger.info("generating initial population...")
        pop = self.initial()
        logger.info("generated initial population")

        logger.info("evaluating initial population...")
        yield from self.evaluate_all(pop, outcomes)
        logger.info("evaluated initial population")

        logger.info("selecting survivors...")
        pop = self.select(pop, outcomes)  # should this happen at the start?
        logger.info("selected survivors")

        for g in range(self.num_generations + 1):
            logger.info(f"starting generation {g}...")
            pop = self.crossover(pop)
            pop = self.mutate(pop)
            logger.info("evaluating candidate patches...")
            outcomes = {}
            yield from self.evaluate_all(pop, outcomes)
            logger.info("evaluated candidate patches")
            pop = self.select(pop, outcomes)
