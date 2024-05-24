Darjeeling Examples
===================

This directory contains a small number of self-contained example repair scenarios.
The prerequisites for each scenario can be installed using the accompanying
:code:`Makefile` for that scenario. :code:`repair.yml` is used to provide a repair
configuration file for each scenario.

To perform the described repair scenario, execute the following from inside the
directory for that scenario:

.. code::

   (poetry) $ darjeeling repair repair.yml

I strongly recommend that you run Darjeeling within a Poetry environment to avoid conflicting with your system's Python installation.
