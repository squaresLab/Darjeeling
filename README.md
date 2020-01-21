# Darjeeling

[![Build Status](https://travis-ci.org/squaresLab/Darjeeling.svg?branch=master)](https://travis-ci.org/squaresLab/Darjeeling)
[![GitQ](https://gitq.com/badge.svg)](https://gitq.com/squaresLab/Darjeeling)

Darjeeling is a language-agnostic search-based program repair tool.
Unlike other repair tools, such as GenProg, SPR, and Nopol, Darjeeling
delegates the responsibility of generating patches, obtaining coverage,
analyzing code, and executing tests to other services.
Once those auxillary concerns are removed, what is left is a lightweight
framework for composing and executing repair algorithms: Darjeeling.


## Features

* *Language Agnostic:* delegates syntax transformation and static analysis to
  other services.
* *Containerization:* uses [Docker](https://www.docker.com/)
  to quickly and safely evaluate patches without executing arbitrary code on
  your machine.
* *Custom Repair Templates:* uses
  [Rooibos](https://github.com/squaresLab/Rooibos) to support rich, custom
  repair templates for arbitrary languages.
* *Asynchronous Evaluation:* accelerates patch evaluation by spreading the
  load across multiple threads.
* *Test Redundancy Checking:* uses coverage information to skip test
  executions that can't be affected by a given patch.
* *Test Ordering:* numerous test ordering schemes reduce the
  cost of patch evaluation by prioritizing likely failing tests.
* *Equivalent Patch Detection:* uses static analysis to
  [remove duplicate transformations](https://squareslab.github.io/papers-repo/pdfs/weimer-ase2013-preprint.pdf)
  from the search space.

## Installation

### Prerequisites

To use Darjeeling, 
[Docker](https://docs.docker.com/install/linux/docker-ce/ubuntu) must be
installed on your machine, and your user account must be a member of the
`docker` group in order [to avoid problems related to insufficient privileges](https://docs.docker.com/install/linux/linux-postinstall)
.
Python 3.5 or greater and [pip3](https://pip.pypa.io/en/stable/installing/)
must also be installed; Darjeeling will not work with older versions of Python
3 nor will it work with any versions of Python 2.

### Optional Extras

We strongly recommend that you install either
[virtualenv](https://virtualenv.pypa.io/en/stable/) or
[pipenv](https://pipenv.readthedocs.io/en/latest/) to contain your installation
of Darjeeling and to avoid conflicting with system packages. Both of packages
can be installed via `pip` as follows:

```
$ pip install virtualenv
$ pip install pipenv
```

Using `virtualenv`, you should create a virtual environment for Darjeeling
either in a new directory or at the root of your clone of this repository:

```
$ virtualenv name_of_directory
```

To enter the virtual environment:

```
$ cd name_of_directory
$ source activate
(venv) $ ...
```

To exit the virtual environment:

```
(venv) $ deactivate
```

### Darjeeling

To install the latest stable release of Darjeeling from PyPI from inside the
virtual environment:

```
(venv) $ pip install darjeeling
```

Alternatively, to install from source, execute the following inside the virtual
environment:

```
(venv) $ pip install .
```

## Usage

Darjeeling exposes a command-line interface (CLI) for performing program
repair, as demonstrated below. The CLI provides a single command, `repair`,
which accepts the path to a Darjeeling configuration file format, described
below.

```
$ darjeeling repair my-config.yml
```

## Configuration File Format (v1.0)

The Darjeeling configuration file format is written in YAML. Below is an
example of a configuration file.

```
version: '1.0'
snapshot: 'manybugs:python:69223-69224'
language: c
seed: 0
threads: 16
localization:
  type: spectrum
  metric: tarantula
  exclude-files:
    - foo.c
algorithm:
  type: exhaustive
transformations:
  schemas:
    - type: delete-statement
    - type: replace-statement
    - type: prepend-statement
optimizations:
  ignore-equivalent-prepends: yes
  ignore-dead-code: yes
  ignore-string-equivalent-snippets: yes
resource-limits:
  candidates: 5000
  time-minutes: 3600
```

Below, we describe the top-level options exposed by the configuration file:

* `version`: the version of the Darjeeling configuration file format
  that was used to write the file.
* `snapshot`: the name of the [BugZoo](https://github.com/squaresLab/BugZoo)
  snapshot that should be used to provide the bug as a Docker container.
* `seed`: a seed for the random number generator.
* `threads`: number of threads over which the repair workload should be
  distributed.
* `limits`: limits on the resources that may be consumed during the search.

### `language`

The `language` property specifies the language used by the program under
repair. Although Darjeeling supports multiple languages, it is not yet
possible to fix bugs that involve more than one language.

Below is a list of the languages that are fully supported by Darjeeling.
Darjeeling can automatically perform static analysis and compute coverage
information for each of these languages.

* *C:* `c`
* *C++:* `cpp`
* *Python:* `python` **(added in Jan. 2020)**

The `text` option (i.e., `language: text`) may be used to ignore the language
of the program under repair and to treat each file as a text file. When this
option is used, users will need to manually provide coverage information, and
static analysis will not be performed.

### `localization`

The `localization` section provides instructions for localizing the fault
inside the program under repair. Currently, the configuration file
format supports a single `type` of fault localization: spectrum-based fault
localization, which assigns a suspiciousness value to each line in
the program under repair based on the number of passing and failing tests
that touch that line. A *suspiciousness metric* is used to compute
individual suspiciousness values. The configuration file exposes a number of
metrics via its `metric` property:

* `tarantula`
* `genprog`
* `jaccard`
* `ochiai`

The `localization` section also exposes an `exclude-files` property, which may
be used to exclude certain files from the fault localization. Each file should
be given by its location relative to the source directory for the program
under repair.
In the example below, the files `foo.c` and `bar.c` are excluded from the fault
localization.

```
exclude-files:
  - foo.c
  - bar.c
```

Individual source code lines can also be excluded using the `exclude-lines`
property, as shown below. The `exclude-lines` property states which lines should
be excluded from specified files. In the example below, lines 1, 2, 3 and 4 from
`foo.c`, and lines 4, 6, 7 from `bar.c` are excluded from the fault
localization.

```
exclude-lines:
  foo.c: [1, 2, 3, 4]
  bar.c: [4, 6, 7]
```

The fault localization can also be restricted to only consider certain files
by using the `restrict-to-files` property, as shown below.

```
restrict-to-files:
  - foo.c
```

Similarly, the fault localization can also be restricted to individual source
code lines using the `restrict-to-lines` property:

```
restrict-to-lines:
  foo.c: [11, 14, 16]
```


### `algorithm`

The `algorithm` section outlines the search algorithm that should be used
to search the space of candidate repairs. A description of the types of
search algorithm exposed by the configuration file format is given below.

* `exhaustive`: iterates over all single-transformation patches within
  the search space until the termination criteria are met.
* `genetic`: implements a customisable genetic algorithm, inspired by
  [GenProg](https://squareslab.github.io/genprog-code/).

### `transformations`

The `transformations` section describes the space of program transformations
from which candidate patches should be composed. The `schemas` property of
this section specifies a list of the program transformation schemas, along
with any parameter values for those schemas, that should may be used to
construct concrete program transformations. Each entry in the `schemas`
list must specify a `type`.

The configuration format supports three "classical" statement-based
transformation schemas based on those introduced by
[GenProg](https://squareslab.github.io/genprog-code/):
`delete-statement`, `replace-statement`, and `prepend-statement`;
`swap-statement` has not been implemented at the time of writing.
To learn more about why Darjeeling uses `prepend-statement` rather than the
traditional `append-statement` schema, see the
[Darjeeling design document](https://github.com/squaresLab/Darjeeling/blob/transformations/docs/design.md).
Below is an example of `schemas` property that uses all of the classical
statement-based schemas.

```
schemas:
  - type: delete-statement
  - type: replace-statement
  - type: prepend-statement
```

The configuration format also supports custom repair templates via
match-rewrite patterns for [Rooibos](https://github.com/squaresLab/Rooibos).
Below is an example of a simple repair template that replaces all calls to
`foo` with calls to `bar`.

```
- type: template
  match: "foo(:[1])"
  rewrite: "bar(:[1])"
```

The `type` property is set to `template` to indicate that this schema
represents a Rooibos-based repair template. The `match` and `rewrite`
sections are used to specify match and rewrite patterns, respectively.

Darjeeling also provides support for naive line-based transformations,
given below, which can be used for programs that use languages that are
not fully supported (i.e., programs that use the `text` language).

```
- type: delete-line
- type: insert-line
- type: replace-line
```

### `optimizations`

The `optimizations` section is used to toggle various optimizations available
to the repair process. By default, all optimizations are enabled. Below is a
list of optimizations that can be toggled by the configuration file.

* `use-scope-checking`: ensures that all variable and function references
  that occur in a given transformation are visible from the scope into
  which they are being inserted.
* `use-syntax-scope-checking`: ensures that any keywords introduced by a
  transformation (e.g., `break` and `continue`) are permitted by their
  surrounding context.
* `ignore-dead-code`: prevents the insertion of code that exclusively
  writes to dead variables.
* `ignore-equivalent-prepends`: uses an approach inspired by
  instruction scheduling to prevent equivalent insertions of code.
* `ignore-untyped-returns`: prevents insertion of a `return` statement into
  a context where the type of the retval is incompatible with the return type
  of the enclosing method or function.
* `ignore-string-equivalent-snippets`: transforms donor code snippets into
  their canonical form, thus preventing the insertion of string-equivalent
  snippets.
* `ignore-decls`: prevents transformations that are either applied to declaration
  statements, or else solely introduce a declaration statement.
* `only-insert-executed-code`: prevents the insertion of code that has not been
  executed by at least one test case.

### `resource-limits`

The `resource-limits` section of the configuration file is used to impose
limits on the resources that may be consumed during the search. The search will
be terminated upon hitting any of these limits. The limits specified in this
section of the configuration file may be overridden by command-line options. If
a limit for a particular resource is not given in either the configuration
file or as a command-line argument, then the use of that resource will be
unbounded (i.e., no limit will be imposed).

Below is a list of the resource limits that may be specified in the
configuration file:

* `candidates`: the maximum number of candidate patches that may be evaluated.
  May be overriden at the command line by the `--max-candidates` option.
* `time-minutes`: the maximum length of wall-clock time that may be spent
  searching for a patch, given in minutes.
  May be overriden at the command line by the `--max-time-mins` option.


## Search Algorithms

This section describes the different search algorithms that are supported by
Darjeeling.

### `exhaustive`

The `exhaustive` search algorithm exhaustively searches over all legal
single-transformation patches within the search space until the termination
criteria are fulfilled.


### `genetic`

The `genetic` search algorithm implements a genetic algorithm that is inspired
by the one used by [GenProg](https://squareslab.github.io/genprog-code/), a
formative search-based program repair tool for C. Below is an excerpt from a
configuration file that uses a `genetic` search algorithm.

```
algorithm:
  type: genetic
  population: 80
  generations: 20
  tournament-size: 3
  mutation-rate: 0.6
  crossover-rate: 0.1
  test-sample-size: 0.4
```

Below is a list of the parameters that are exposed by `genetic`:

* `population`: the size of the (initial) population. Used to control the
  number of individuals that are selected as parents.
* `generations`: the maximum number of generations.
* `tournament-size`: the size of the tournament when performing tournament
  selection to choose parents. Larger tournament sizes lead to an increased
  selective pressure.
* `mutation-rate`: the probability of an individual mutation event.
* `crossover-rate`: the probability of an individual crossover event between
  two parents.
* `test-sample-size`: controls test sampling. When test sampling is
  enabled, the fitness of an individual is computed using a randomly selected
  subset of the test suite, rather than the entire test suite. (More specifically,
  test sampling selects a subset of the passing tests whilst keeping all of the
  failing tests.)
  The value of `test-sample-size` is used to specify the size of the subset
  (or *sample*). If `test-sample-size` is given as a float, then it will be
  treated as a fraction. If `test-sample-size` is given as an integer, then its
  value will be used as the absolute number of (passing) tests that should be
  included in the sample. If `test-sample-size` is omitted or set to `null`,
  test sampling will be disabled.


## Extending Darjeeling via Plugins

Users may extend Darjeeling's capabilities with their own plugins.
Upon launch, Darjeeling will find and automatically import all installed
Python packages whose name starts with `darjeeling_` (e.g.,
`darjeeling_ardupilot`).

Darjeeling treats the following features as framework extension points,
allowing variants to be added by plugins:

* Search algorithms
* Transformation schemas
* Test harnesses
* Coverage tools (e.g., `jacoco`, `pycoverage`, `sancov`)
* Spectrum-based fault localisation suspiciousness metrics
