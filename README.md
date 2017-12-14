# Darjeeling

Language-independent automated program repair

## Inputs

* Access to the source code for the program under repair.
* A set of executable instructions for building a Docker image for the program
  under repair.
* A description of the available local and remote compute facilities
  (i.e., *nodes*) that should be made available to the repair process.
  Darjeeling will distribute the repair process over these nodes.
* A set of resource limits (e.g., maximum wall-clock time, maximum test
  suite evaluations, maximum candidate evaluations, etc.).
