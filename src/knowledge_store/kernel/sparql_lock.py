"""One lock for rdflib's SPARQL parser.

rdflib parses SPARQL with pyparsing, which is not thread-safe while it parses. Two threads
parsing at once fail with TypeError("Param.postParse2() missing ... 'tokenList'"). pySHACL
parses the shapes' SPARQL constraints during validation, and the private workbench parses
the agent's queries, so both take this lock. Only parsing needs it: a prepared query runs
without it.
"""

from __future__ import annotations

import threading

PARSE_LOCK = threading.RLock()
