__all__ = ['GeneticSearcher']

from typing import Iterator
import concurrent.futures
import logging

from .base import Searcher
from ..candidate import Candidate

logger = logging.getLogger(__name__)  # type: logging.Logger
logger.setLevel(logging.DEBUG)

Population = List[Individual]


class GeneticSearcher(Searcher):
    def __init__(self,
                 bugzoo: bugzoo.BugZoo,
                 problem: Problem,
                 *,
                 population_size: int = 40,
                 num_generations: int = 10,
                 rate_crossover: float = 1.0,
                 rate_mutation: float = 1.0,
                 tournament_size: int = 3,
                 threads: int = 1,
                 time_limit: Optional[datetime.timedelta] = None,
                 candidate_limit: Optional[int] = None
                 ) -> None:
        self.__population_size = population_size
        self.__num_generations = num_generations
        self.__rate_crossover = rate_crossover
        self.__rate_mutation = rate_mutation
        self.__tournament_size = tournament_size
        super().__init__(bugzoo,
                         problem,
                         threads=threads,
                         time_limit=time_limit,
                         candidate_limit=candidate_limit)

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
        pop = Population([Candidate() for _ in self.population_size])
        return self.mutate(pop)

    def choose_transformation(self) -> Transformation:
        raise NotImplementedError

    def evaluate(self, pop: Population) -> Iterator[Candidate]:
        for candidate in pop:
            self.evaluator.submit(candidate)
        for candidate, outcome in self.evaluator.as_completed():
            if outcome.is_repair:
                yield candidate

    def fitness(self, population: Population) -> Dict[Candidate, float]:
        """
        Computes the fitness of each individual within a population.
        """
        f = {}  # type: Dict[Individual, float]
        for ind in population:
            outcome = self.outcomes[ind]
            if not outcome.build.successful:
                f[ind] = 0.0
            else:
                # FIXME maybe we don't need to execute the test?
                raise NotImplementedError
        return f

    def select(self, population: Population) -> Population:
        """
        Selects N individuals from the population to survive into the
        next generation.
        """
        survivors = Population()
        ind_to_fitness = self.fitness(population)
        for _ in self.population_size:
            participants = random.sample(pop, self.tournament_size)
            winner = max(participants, key=fitness.__getitem__)
            survivors.append(winner)
        return survivors

    def mutate(self, pop: Population) -> Population:
        offspring = Population()
        for ind in pop:
            child = ind
            if random.random() <= self.rate_mutation:
                mutation = self.choose_transformation()
                tx = frozenset(child.transformations | {mutation})
                child = Candidate(tx)
            offspring.append(child)
        return offspring

    def crossover(self, pop: Population) -> Population:
        def one_point_crossover(px: Candidate, py: Candidate) -> Candidate:
            tx = list(px.transformations)
            ty = list(py.transformations)

            lx = random.randint(0, len(tx))
            ly = random.randint(0, len(ty))

            a, b = tx[:lx], tx[lx:]
            c, d = ty[:ly], ty[ly:]

            return [Candidate(a + d),
                    Candidate(c + b)]

        offspring = Population()
        pop = random.shuffle(pop)
        for i in range(0, len(pop), 2):
            parents = pop[i:i+n]
            offspring += parents
            if len(parents) == 2 and random.random() <= self.rate_crossover:
                offspring += one_point_crossover(*parents)
        return offspring

    def run(self) -> Iterator[Candidate]:
        logger.info("generating initial population...")
        pop = self.initial()
        logger.info("generated initial population")

        yield from self.evaluate(pop)
        pop = self.select(pop)  # should this happen at the start?

        for g in range(0, self.num_generations + 1):
            pop = self.crossover(pop)
            pop = self.mutate(pop)
            yield from self.evaluate(pop)
            pop = self.select(pop)
