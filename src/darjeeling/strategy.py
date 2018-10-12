from typing import Iterator, List
import random

from .candidate import Candidate
from .transformation import Transformation

Population = List[Individual]


class Strategy(object):
    pass


@attr.ib(frozen=True)
class ExhaustiveStrategy(Strategy):
    pass


@attr.ib(frozen=True)
class RSRepairStrategy(Strategy):
    pass


@attr.ib(frozen=True)
class GreedyStrategy(Strategy):
    pass


@attr.ib(frozen=True)
class GenProgStrategy(Strategy):
    population_size = attr.ib(type=int)
    num_generations = attr.ib(type=int)
    rate_crossover = attr.ib(type=float)
    rate_mutation = attr.ib(type=float)
    tournament_size = attr.ib(type=int)

    # sample strategy: [variant, generation, all]
    # sample size
    # best test rule: [test prioritisation / test selection]

    # use futures? submit individual + tests?

    # - compute test stats between generations?

    def initial(self) -> Population:
        """
        Generates an initial population according to this strategy.
        """
        pop = Population([Candidate() for _ in self.population_size])
        return self.mutate(pop)

    def choose_transformation(self) -> Transformation:
        raise NotImplementedError

    def fitness(self, population: Population) -> Dict[Individual, float]:
        """
        Computes the fitness of each individual within a population.
        """
        # what tests are in our sample?
        f = {}  # type: Dict[Individual, float]
        for ind in population:
            built = False
            if not built:
                f[ind] = 0.0
            else:
                # maybe we don't need to execute the test?
                pass
        raise NotImplementedError

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
                child = Individual(tx)
            offspring.append(child)
        return offspring

    def crossover(self, pop: Population) -> Population:
        def one_point_crossover(px: Individual, py: Individual) -> Individual:
            tx = list(px.transformations)
            ty = list(py.transformations)

            lx = random.randint(0, len(tx))
            ly = random.randint(0, len(ty))

            a, b = tx[:lx], tx[lx:]
            c, d = ty[:ly], ty[ly:]

            return [Individual(a + d),
                    Individual(c + b)]

        offspring = Population()
        pop = random.shuffle(pop)
        for i in range(0, len(pop), 2):
            parents = pop[i:i+n]
            offspring += parents
            if len(parents) == 2 and random.random() <= self.rate_crossover:
                offspring += one_point_crossover(*parents)
        return offspring

    def run(self) -> Iterator[Candidate]:
        pop = self.initial()
        for g in range(0, self.num_generations + 1):
            pop = self.crossover(pop)
            pop = self.mutate(pop)

            # choose tests
            evaluate(pop)  # TODO test sampling
            pop = self.select(pop)
