# Darjeeling

[![Build Status](https://travis-ci.org/squaresLab/Darjeeling.svg?branch=master)](https://travis-ci.org/squaresLab/Darjeeling)

Darjeeling is a work-in-progress language-independent automated program repair
tool. Unlike other repair tools such as GenProg, SPR, and Nopol, Darjeeling
delegates the responsibility of generating patches, obtaining coverage,
analysing code, and executing tests to other services. (For the most part, those
other services are also language independent.)
Once those auxillary concerns are removed, what is left is a lightweight
framework for composing and executing repair algorithms: Darjeeling.


## Features

* Multi-threaded asynchronous patch evaluation: maximises throughput by
  distributing patch evaluation across multiple threads using an asychronous
  queue.
* Test case reduction: test outcomes that can't be affected by a given patch,
  as determined by coverage information, are skipped during patch evaluation.


## Installation

We recommend that you use `pipenv` to install Darjeeling, although `pip3` or
`easy_install` may be used instead:

```
$ pipenv install darjeeling
```

Darjeeling supports Python >= 3.5.


## Usage

Provide a "Hello World" example.


## Configuration File Format (v1.0)

```
version: '1.0'
snapshot: 'manybugs:python:69223-69224'
seed: 0
threads: 16
localization:
  type: spectrum
  metric: tarantula
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
```

Below, we describe the top-level options exposed by the configuration file:

* `version`: the version of the Darjeeling configuration file format
  that was used to write the file.
* `snapshot`: the name of the [BugZoo](https://github.com/squaresLab/BugZoo)
  snapshot that should be used to provide the bug as a Docker container.
* `seed`: a seed for the random number generator.
* `threads`: number of threads over which the repair workload should be
  distributed.

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

### `algorithm`

The `algorithm` section outlines the search algorithm that should be used
to search the space of candidate repairs. A description of the types of
search algorithm exposed by the configuration file format is given below.

* `random`

### `transformations`

The `transformations` section describes the space of program transformations
from which candidate patches should be composed. The `schemas` property of
this section specifies which program transformation schemas may be used to
construct the program transformations. The configuration format currently
supports three transformation schemas: `delete-statement`,
`replace-statement`, and `prepend-statement`.

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
