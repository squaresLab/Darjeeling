Darjeeling
==========

.. image:: https://travis-ci.org/squaresLab/Darjeeling.svg?branch=master
    :target: https://travis-ci.org/squaresLab/Darjeeling

.. image:: https://gitq.com/badge.svg
    :target: https://gitq.com/squaresLab/Darjeeling

Darjeeling is a language-agnostic search-based program repair tool.
Unlike other repair tools, such as GenProg, SPR, and Nopol, Darjeeling
delegates the responsibility of generating patches, obtaining coverage,
analyzing code, and executing tests to other services.
Once those auxillary concerns are removed, what is left is a lightweight
framework for composing and executing repair algorithms: Darjeeling.


Features
--------

* *Language Agnostic:* delegates syntax transformation and static analysis to
  other services.
* *Containerization:* uses `Docker <https://www.docker.com/>`_
  to quickly and safely evaluate patches without executing arbitrary code on
  your machine.
* *Custom Repair Templates:* uses
  `Rooibos <https://github.com/squaresLab/Rooibos>`_ to support rich, custom
  repair templates for arbitrary languages.
* *Asynchronous Evaluation:* accelerates patch evaluation by spreading the
  load across multiple threads.
* *Test Redundancy Checking:* uses coverage information to skip test
  executions that can't be affected by a given patch.
* *Test Ordering:* numerous test ordering schemes reduce the
  cost of patch evaluation by prioritizing likely failing tests.
* *Equivalent Patch Detection:* uses static analysis to
  `remove duplicate transformations <https://squareslab.github.io/papers-repo/pdfs/weimer-ase2013-preprint.pdf>`_
  from the search space.


Installation
------------

Prerequisites
.............

To use Darjeeling,
`Docker <https://docs.docker.com/install/linux/docker-ce/ubuntu>`_ must be
installed on your machine, and your user account must be a member of the
:code:`docker` group in order `to avoid problems related to insufficient privileges <https://docs.docker.com/install/linux/linux-postinstall>`_
.
Python 3.9 or greater and `pip3 <https://pip.pypa.io/en/stable/installing>`_ must also be installed; Darjeeling will not work with older versions of Python 3 nor will it work with any versions of Python 2.

Optional Extras
...............

We strongly recommend that you use `pipenv <https://pipenv.readthedocs.io/en/latest>`_ to contain your installation of Darjeeling and avoid conflicting with system packages. To install pipenv, execute the following command:

.. code::

   $ pip install pipenv

Darjeeling
..........

To install Darjeeling from source via pipenv, execute the following from the root of the repository:

.. code::

  $ pipenv install


Usage
-----

After installing Darjeeling via pipenv as shown above, you can drop into the newly created virtual environment by executing the following command from the root of the repository:

.. code::

  $ pipenv shell

To exit from the virtual environment, you can execute the following command:

.. code::

  (Darjeeling) $ exit

Darjeeling exposes a command-line interface (CLI) for performing program
repair, as demonstrated below. The CLI provides a single command, `repair`,
which accepts the path to a Darjeeling configuration file format, described
below.

.. code::

   $ darjeeling repair my-config.yml


Configuration File Format (v1.0)
--------------------------------

The Darjeeling configuration file format is written in YAML. Below is an
example of a configuration file. The configuration file itself can be
found in the `example/gcd <example/gcd>`_ directory.

.. code:: yaml

   version: '1.0'
   seed: 0
   threads: 16

   # provides information about the program under repair, including
   # the name of the Docker image that is used to provide it, the
   # location of the source code for the program within that image,
   # and instructions for building and testing it.
   program:
     image: darjeeling/example:gcd
     language: c
     source-directory: /experiment/source
     build-instructions:
       time-limit: 10
       steps:
         - gcc gcd.c -o gcd
       steps-for-coverage:
         - gcc gcd.c -o gcd --coverage
     tests:
       type: genprog
       workdir: /experiment
       number-of-failing-tests: 1
       number-of-passing-tests: 10
       time-limit: 5

   # specifies the method/tool that should be used to obtain coverage for
   # the program.
   coverage:
     method:
       type: gcov
       files-to-instrument:
         - gcd.c

   localization:
     type: spectrum
     metric: tarantula

   algorithm:
     type: exhaustive

   transformations:
     schemas:
       - type: delete-statement
       - type: replace-statement
       - type: append-statement

   optimizations:
     ignore-equivalent-insertions: yes
     ignore-dead-code: yes
     ignore-string-equivalent-snippets: yes

   # places a limit on the resources (e.g., wall-clock time, test executions,
   # candidate patches) that may be consumed during the search for a repair.
   resource-limits:
     candidates: 100


Below, we describe the top-level options exposed by the configuration file:

* :code:`version`: the version of the Darjeeling configuration file format
  that was used to write the file.
* :code:`seed`: a seed for the random number generator.
* :code:`threads`: number of threads over which the repair workload should be
  distributed.

:code:`program`
...............

The :code:`program` section is used to provide essential details about the
program that should be repaired. This section contains the following
properties:

* :code:`image`: the name of the Docker image that provides the program
  under repair.
* :code:`source-directory`: the absolute path of the source code for the program
  within the provided Docker image.
* :code:`language`: the language used by the program under repair. Note that,
  although Darjeeling supports multiple languages, it is not currently possible
  to fix bugs that involve more than one language.
* :code:`build-instructions`: executable instructions for (re-)building the
  program inside the container. Discussed below.
* :code:`tests`: details of the test suite used by the program. Discussed below.

:code:`program.language`
~~~~~~~~~~~~~~~~~~~~~~~~

Below is a list of the languages that are fully supported by Darjeeling.
Darjeeling can automatically perform static analysis and compute coverage
information for each of these languages.

* *C:* :code:`c`
* *C++:* :code:`cpp`
* *Python:* :code:`python`

The :code:`text` option (i.e., `language: text`) may be used to ignore the language
of the program under repair and to treat each file as a text file. When this
option is used, users will need to manually provide coverage information, and
static analysis will not be performed.

:code:`program.build-instructions`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This section provides instructions to Darjeeling for re-building the program
for purposes of (a) evaluating candidate patches, and (b) instrumenting the
program for coverage collection. Below is an except of the
:code:`build-instructions` section from the example above.

.. code:: yaml

   build-instructions:
      time-limit: 10
      steps:
        - gcc gcd.c -o gcd
      steps-for-coverage:
        - gcc gcd.c -o gcd --coverage


The :code:`time-limit` specifies the maximum number of seconds that Darjeeling
should wait before cancelling a build attempt. The :code:`steps` property
provides a sequence of shell commands that are used to build the program
for the purpose of patch evaluation. Similarly, the :code:`steps-for-coverage`
property gives a sequence of shell commands that are used to build the
program with coverage instrumentation.


:code:`program.tests`
~~~~~~~~~~~~~~~~~~~~~

This section is used to describe the test suite used by the program.
Darjeeling uses the program's test suite to determine the correctness
of patches and to find acceptable patches that pass all tests.
Darjeeling offers a number of test suite options out of the box,
specified by the :code:`type` property within the :code:`tests`
section. We describe these below.

:code:`program.tests[type:genprog]`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This type of test suite provides convenient support for GenProg-style test
scripts used by benchmarks such as ManyBugs, IntroClass, and the GenProg TSE
2012 benchmarks. GenProg-style test scripts accept a single argument specifying
the name of the positive or negative test case that should be executed.
Positive tests correspond to tests that pass on the original, unmodified
program, whereas negative tests correpond to tests that fail on the original
program. The positive tests are named using the form :code:`p{k}`, where
:code:`{k}` is replaced by the number of the positive test (starting from 1).
Similarly, negative tests are named :code:`n{k}`, where :code:`{k}` is replaced
by the number of the negative test (starting from 1).

Below is an example of a :code:`genprog` test suite:

.. code:: yaml

     tests:
       type: genprog
       workdir: /experiment
       number-of-failing-tests: 1
       number-of-passing-tests: 10
       time-limit: 5


The :code:`time-limit` property specifies the maximum number of seconds that may elapse
before a test execution is aborted and declared a failure. The
:code:`number-of-passing-tests` and :code:`number-of-failing-tests`
properties state the number of passing and failing tests.
The :code:`workdir` property gives the absolute path of the directory
that contains the :code:`test.sh` for the test harness.

:code:`program.tests[type:pytest]`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This test suite is used by Python programs that support the popular
`pytest <https://docs.pytest.org/en/stable/>`_ framework. Note that
pytest can run `unittest <https://docs.pytest.org/en/stable/unittest.html#unittest>`_
and `nose <https://docs.pytest.org/en/stable/nose.html#noseintegration>`_
tests natively.

Below is an except from a configuration file that uses :code:`pytest`:

.. code:: yaml

  tests:
    type: pytest
    workdir: /opt/flask
    tests:
      - tests/test_config.py::test_get_namespace
      - tests/test_config.py::test_config_from_pyfile
      - tests/test_config.py::test_config_from_object

The :code:`workdir` directory specifies the location at which :code:`pytest`
should be executed. The :code:`tests` property gives a list of the names of
the individual tests belonging to the test suite. Each name is given the
format expected by pytest. That is, the name of the file containing the
test (relative to :code:`workdir`), followed by :code:`::` and the name
of the test method.
**Note that automated discovery of test cases is not currently
implemented, but is planned for a future release.**


:code:`coverage`
................

The :code:`coverage` section provides Darjeeling with instructions for computing
test coverage for the program under repair. Below, we describe the properties
contained within this section:

* :code:`method`: the tool that should be used to compute coverage for the program
  under repair. This information is necessary since Darjeeling deals with multiple
  languages, and each languages may have more than one associated tool for
  obtaining coverage. Out of the box, Darjeeling provides support for :code:`gcov`,
  used for C and C++ programs, and :code:`pycoverage`, used for Python programs.
  Support for additional coverage methods may be added via Darjeeling's plugin
  mechanism.
  Further details on these two methods are provided below.
* :code:`load-from-file`: optionally specifies the location of a file from which
  coverage should be read. An example of such a coverage file can be found in
  `example/flask/coverage.yml <example/flask/coverage.yml>`_.
* :code:`restrict-to-files`: optionally gives a list of files to which the
  coverage collection should be restricted to. Files should be given as paths
  relative to the specified :code:`source-directory` for the program.
  Coverage that is generated for files outside of this set will be automatically
  discarded by Darjeeling. Note that this property uses the same format as
  :code:`localization.restrict-to-files`.
* :code:`restrict-to-lines`: optionally gives a list of lines that the coverage
  coverage collection should be restricted to. Lines outside of this set will be
  automatically ignored.
  This method uses the same format as :code:`localization.restrict-to-lines`,
  shown below.


:code:`gcov`
~~~~~~~~~~~~

Below is an excerpt from an example configuration that uses :code:`gcov` for
coverage collection.

.. code:: yaml

   coverage:
     method:
       type: gcov
       files-to-instrument:
         - gcd.c


This method accepts a single, optional property, :code:`files-to-instrument`.
**This property is very important.**
By default, programs compiled with the appropriate :code:`--coverage` option
set in their :code:`CFLAGS`, :code:`CXXFLAGS`, and :code:`LDFLAGS` will produce
:code:`.gcda` files at runtime. The gcov tool computes coverage by reading both
those :code:`.gcda` files and their associated :code:`.gcno` files, generated
during compilation. More specifically, programs compiled with the :code:`--coverage`
option will write coverage data to disk during the *normal termination* of the
program (i.e., the program exits with code zero). If the program abruptly
terminates (e.g., due to memory corruption), :code:`.gcda` files will NOT be
produced.

This behavior is problematic for Darjeeling. It prevents collection from being
obtained for failing tests that crash the program. As a workaround, Darjeeling
adds source-based instrumentation to the program (in the form of a signal
handler) that causes the program to (attempt to) flush its coverage information
in thee event of abrupt termination. The :code:`files-to-instrument` property
gives the names of the source code files that provide entrypoints to the program
binaries (i.e., :code:`main` functions).


:code:`localization`
....................

The :code:`localization` section provides instructions for localizing the fault
inside the program under repair. Currently, the configuration file
format supports a single :code:`type` of fault localization: spectrum-based fault
localization, which assigns a suspiciousness value to each line in
the program under repair based on the number of passing and failing tests
that touch that line. A *suspiciousness metric* is used to compute
individual suspiciousness values. The configuration file exposes a number of
metrics via its :code:`metric` property:

* :code:`tarantula`
* :code:`genprog`
* :code:`jaccard`
* :code:`ochiai`

The :code:`localization` section also exposes an :code:`exclude-files`
property, which may be used to exclude certain files from the fault
localization. Each file should be given by its location relative to the source
directory for the program under repair.
In the example below, the files :code:`foo.c` and :code:`bar.c` are excluded
from the fault localization.

.. code:: yaml

   exclude-files:
     - foo.c
     - bar.c

Individual source code lines can also be excluded using the :code:`exclude-lines`
property, as shown below. The :code:`exclude-lines` property states which lines should
be excluded from specified files. In the example below, lines 1, 2, 3 and 4 from
:code:`foo.c`, and lines 4, 6, 7 from :code:`bar.c` are excluded from the fault
localization.

.. code:: yaml

   exclude-lines:
     foo.c: [1, 2, 3, 4]
     bar.c: [4, 6, 7]

The fault localization can also be restricted to only consider certain files
by using the :code:`restrict-to-files` property, as shown below.

.. code:: yaml

   restrict-to-files:
     - foo.c

Similarly, the fault localization can also be restricted to individual source
code lines using the :code:`restrict-to-lines` property:

.. code:: yaml

   restrict-to-lines:
     foo.c: [11, 14, 16]


:code:`algorithm`
.................

The :code:`algorithm` section outlines the search algorithm that should be used
to search the space of candidate repairs. A description of the types of
search algorithm exposed by the configuration file format is given below.

* :code:`exhaustive`: iterates over all single-transformation patches within
  the search space until the termination criteria are met.
* :code:`genetic`: implements a customisable genetic algorithm, inspired by
  `GenProg <https://squareslab.github.io/genprog-code>`_.


:code:`transformations`
.......................

The :code:`transformations` section describes the space of program
transformations from which candidate patches should be composed. The
:code:`schemas` property of this section specifies a list of the program
transformation schemas, along with any parameter values for those schemas, that
should may be used to construct concrete program transformations. Each entry in
the :code:`schemas` list must specify a :code:`type`.

The configuration format supports three "classical" statement-based
transformation schemas based on those introduced by
`GenProg <https://squareslab.github.io/genprog-code>`_:
:code:`delete-statement`, :code:`replace-statement`, and :code:`prepend-statement`;
:code:`swap-statement` has not been implemented at the time of writing.
To learn more about why Darjeeling uses :code:`prepend-statement` rather than the
traditional :code:`append-statement` schema, see the
`Darjeeling design document <docs/design.md>`_.
Below is an example of :code:`schemas` property that uses all of the classical
statement-based schemas.

.. code:: yaml

   schemas:
     - type: delete-statement
     - type: replace-statement
     - type: prepend-statement

The configuration format also supports custom repair templates via
match-rewrite patterns for `Rooibos <https://github.com/squaresLab/Rooibos>`_.
Below is an example of a simple repair template that replaces all calls to
:code:`foo` with calls to :code:`bar`.

.. code:: yaml

   - type: template
     match: "foo(:[1])"
     rewrite: "bar(:[1])"

The :code:`type` property is set to :code:`template` to indicate that this schema
represents a Rooibos-based repair template. The :code:`match` and :code:`rewrite`
sections are used to specify match and rewrite patterns, respectively.

Darjeeling also provides support for naive line-based transformations,
given below, which can be used for programs that use languages that are
not fully supported (i.e., programs that use the :code:`text` language).

.. code:: yaml

   - type: delete-line
   - type: insert-line
   - type: replace-line


:code:`optimizations`
.....................

The :code:`optimizations` section is used to toggle various optimizations available
to the repair process. By default, all optimizations are enabled. Below is a
list of optimizations that can be toggled by the configuration file.

* :code:`use-scope-checking`: ensures that all variable and function references
  that occur in a given transformation are visible from the scope into
  which they are being inserted.
* :code:`use-syntax-scope-checking`: ensures that any keywords introduced by a
  transformation (e.g., :code:`break` and :code:`continue`) are permitted by their
  surrounding context.
* :code:`ignore-dead-code`: prevents the insertion of code that exclusively
  writes to dead variables.
* :code:`ignore-equivalent-insertions`: uses an approach inspired by
  instruction scheduling to prevent equivalent insertions of code.
* :code:`ignore-untyped-returns`: prevents insertion of a :code:`return` statement into
  a context where the type of the retval is incompatible with the return type
  of the enclosing method or function.
* :code:`ignore-string-equivalent-snippets`: transforms donor code snippets into
  their canonical form, thus preventing the insertion of string-equivalent
  snippets.
* :code:`ignore-decls`: prevents transformations that are either applied to declaration
  statements, or else solely introduce a declaration statement.
* :code:`only-insert-executed-code`: prevents the insertion of code that has not been
  executed by at least one test case.


:code:`resource-limits`
.......................

The :code:`resource-limits` section of the configuration file is used to impose
limits on the resources that may be consumed during the search. The search will
be terminated upon hitting any of these limits. The limits specified in this
section of the configuration file may be overridden by command-line options. If
a limit for a particular resource is not given in either the configuration file
or as a command-line argument, then the use of that resource will be unbounded
(i.e., no limit will be imposed).

Below is a list of the resource limits that may be specified in the
configuration file:

* :code:`candidates`: the maximum number of candidate patches that may be evaluated.
  May be overriden at the command line by the :code:`--max-candidates` option.
* :code:`time-minutes`: the maximum length of wall-clock time that may be spent
  searching for a patch, given in minutes.
  May be overriden at the command line by the :code:`--max-time-mins` option.


Search Algorithms
-----------------

This section describes the different search algorithms that are supported by
Darjeeling.


:code:`exhaustive`
..................

The :code:`exhaustive` search algorithm exhaustively searches over all legal
single-transformation patches within the search space until the termination
criteria are fulfilled.

:code:`genetic`
...............

The :code:`genetic` search algorithm implements a genetic algorithm that is inspired
by the one used by `GenProg <https://squareslab.github.io/genprog-code>`_, a
formative search-based program repair tool for C. Below is an excerpt from a
configuration file that uses a :code:`genetic` search algorithm.

.. code:: yaml

   algorithm:
     type: genetic
     population: 80
     generations: 20
     tournament-size: 3
     mutation-rate: 0.6
     crossover-rate: 0.1
     test-sample-size: 0.4


Below is a list of the parameters that are exposed by :code:`genetic`:

* :code:`population`: the size of the (initial) population. Used to control the
  number of individuals that are selected as parents.
* :code:`generations`: the maximum number of generations.
* :code:`tournament-size`: the size of the tournament when performing tournament
  selection to choose parents. Larger tournament sizes lead to an increased
  selective pressure.
* :code:`mutation-rate`: the probability of an individual mutation event.
* :code:`crossover-rate`: the probability of an individual crossover event between
  two parents.
* :code:`test-sample-size`: controls test sampling. When test sampling is
  enabled, the fitness of an individual is computed using a randomly selected
  subset of the test suite, rather than the entire test suite. (More specifically,
  test sampling selects a subset of the passing tests whilst keeping all of the
  failing tests.)
  The value of :code:`test-sample-size` is used to specify the size of the subset
  (or *sample*). If :code:`test-sample-size` is given as a float, then it will be
  treated as a fraction. If :code:`test-sample-size` is given as an integer, then its
  value will be used as the absolute number of (passing) tests that should be
  included in the sample. If :code:`test-sample-size` is omitted or set to
  :code:`null`, test sampling will be disabled.


Extending Darjeeling via Plugins
--------------------------------

Users may extend Darjeeling's capabilities with their own plugins.
Upon launch, Darjeeling will find and automatically import all installed
Python packages whose name starts with :code:`darjeeling_` (e.g.,
:code:`darjeeling_ardupilot`).

Darjeeling treats the following features as framework extension points,
allowing variants to be added by plugins:

* Search algorithms
* Transformation schemas
* Test harnesses
* Coverage tools (e.g., :code:`jacoco`, :code:`pycoverage`, :code:`sancov`)
* Spectrum-based fault localisation suspiciousness metrics
