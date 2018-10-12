from typing import Iterator, List
import random

from .candidate import Candidate
from .transformation import Transformation

Population = List[Individual]


class Strategy(object):
    pass




@attr.ib(frozen=True)
class GenProgStrategy(Strategy):
    population_size = attr.ib(type=int)
    num_generations = attr.ib(type=int)
    rate_crossover = attr.ib(type=float)
    tournament_size = attr.ib(type=int)

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

    def mutate(self, population: Population) -> Population:
        offspring = Population()
        for ind in offspring:
            t = self.choose_transformation()
            child = frozenset(ind.transformations | {t})
            offspring.append(child)
        return offspring

    def crossover(self, pop: Population) -> Population:
        offspring = Population()
        pop = random.shuffle(pop)
        size = len(pop)
        for i in range(0, size, 2):
            parents = pop[i:i+n]
            offspring += parents
            if len(parents) == 2 and random.random() <= self.rate_crossover:
                child = self.one_point_crossover(px, py)
                offspring.append(child)
        return offspring

    def run(self) -> Iterator[Candidate]:
        pop = self.initial()
        for g in range(0, self.num_generations + 1):
            pop = self.crossover(pop)
            pop = self.mutate(pop)
            pop = self.select(pop)
