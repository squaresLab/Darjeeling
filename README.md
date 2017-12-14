# Darjeeling

Language-independent automated program repair

## Inputs

Darjeeling should be provided with a description of the program under repair,
which is supplied by the following:

* The source code.
* A set of executable instructions for building a Docker image for the program
  under repair.

Additionally, Darjeeling should be provided with a description of the compute
resources that should be used by the repair, given by the following:

* A description of the available local and remote compute facilities
  (i.e., *nodes*) that should be made available to the repair process.
  Darjeeling will distribute the repair process over these nodes.
* A set of resource limits (e.g., maximum wall-clock time, maximum test
  suite evaluations, maximum candidate evaluations, etc.).
