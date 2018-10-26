Design of Darjeeling
====================

This document discusses some of the design decisions made during the
development of Darjeeling.


Prepend Statement
-----------------

Unlike the majority of search-based program repair tools that implement
GenProg-style statement transformations, Darjeeling relies on
a prepending (rather than appending) statements to insert new statements
into the program.
By restricting the only prepending before statements, liveness and scope
information only needs to be computed immediately before the statement.
In contrast, GenProg computes the set of variables that are live before
*and* after a given statement. Unfortunately, Clang's liveness analysis
API only exposes the set of variables that are live before a statement.
Since `append-statement` is the only transformation that requires knowledge
of the set of variables that are live after the target statement, we can
avoid the need to compute this information by using `prepend-statement`
instead.
