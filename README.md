# Darjeeling

Language-independent automated program repair

## Inputs

### Program Under Repair

Darjeeling should be provided with a description of the program under repair,
which is supplied by the following:

* The path to the directory containing the source code for the program.
* Instructions for building a Docker image for the program.

Below is an example program description in JSON form:

```
{
  "source": "/home/chris/php",
  "build": {
    "file": "Dockerfile",
    "args": {}
  }
}
```

### Compute Nodes

Additionally, Darjeeling should be provided with a list of the compute
nodes that should be made available to the repair process. Each of those
resources should be described by the following:

* URI of the Docker daemon on the node.
* Number of logical cores.

### Resource Limits

Finally, Darjeeling should be provided with a set of resource limits that
specify how many resources the repair process may consume before
terminating. These resource limits include:

* Maximum wall-clock time taken by repair.
* Maximum number of test suite evaluations.
* Maximum number of candidate repair evaluations.
