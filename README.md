# Darjeeling

Language-independent automated program repair

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
$ python3.6 -m venv .
$ source bin/activate
$ pip install . --upgrade
$ git clone https://github.com/squaresLab/BugZoo bugzoo
$ (cd bugzoo && pip install . --upgrade)
```

## Usage

Provide a "Hello World" example.
