# Darjeeling

Language-independent automated program repair

## Inputs

```json
{
  "program": { ... },
  "nodes": [
    ...
  ],
  "limits": {
    ...
  }
}
```

### Program Under Repair

Darjeeling should be provided with a description of the program under repair,
which is supplied by the following:

* The path to the directory containing the source code for the program.
* Instructions for building a Docker image for the program.

Below is an example program description.

```json
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

Below is an example list of compute nodes.

```json
[
  {
    "uri": "192.168.0.1:6000",
    "cores": 4
  },
  {
    "uri": "52.90.113.128:6000",
    "cores": 2
  }
]
```

### Resource Limits

Finally, Darjeeling should be provided with a set of resource limits that
specify how many resources the repair process may consume before
terminating. These resource limits include:

* Maximum wall-clock time taken by repair.
* Maximum number of test suite evaluations.
* Maximum number of candidate repair evaluations.


## Approach

Uses Relix and Rooibos to do all of the heavy lifting!

* Uses Relix to safely collect coverage information and to evaluate candidate
  patches. Darjeeling distributes the repair process over multiple machines
  by using Relix to provision and interact with Docker containers on those
  machines.

## Installation

```
$ pip3 install darjeeling
```

## Usage

Provide a "Hello World" example.
