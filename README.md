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
* *Containerization:* uses [BugZoo](https://github.com/squaresLab/BugZoo)
  to quickly and safely evaluate patches without executing arbitrary code on
  your machine.
* *Custom Repair Templates:* uses
  [Rooibos](https://github.com/squaresLab/Roobios) to support rich, custom
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

To unlock all of Darjeeling's features, including template-based repair,
[Rooibos](https://github.com/squaresLab/Rooibos) and
[Rooibosd](https://github.com/squaresLab/rooibosd) must be installed.

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
seed: 0
threads: 16
localization:
  type: spectrum
  metric: tarantula
  exclude-files:
    - foo.c
algorithm:
  type: random
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


### `algorithm`

The `algorithm` section outlines the search algorithm that should be used
to search the space of candidate repairs. A description of the types of
search algorithm exposed by the configuration file format is given below.

* `random`
* `genetic`

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
