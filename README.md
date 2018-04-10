# Darjeeling

[![Build Status](https://travis-ci.org/squaresLab/Darjeeling.svg?branch=master)](https://travis-ci.org/squaresLab/Darjeeling)

Darjeeling is a work-in-progress language-independent automated program repair
tool. Unlike other repair tools such as GenProg, SPR, and Nopol, Darjeeling
delegates the responsibility of generating patches, obtaining coverage,
analysing code, and executing tests to other services. (For the most part, those
other services are also language independent.)
Once those auxillary concerns are removed, what is left is a lightweight
framework for composing and executing repair algorithms: Darjeeling.

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
