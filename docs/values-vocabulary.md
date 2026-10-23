# Knowledge Store value kinds

Namespace `https://w3id.org/knowledge-store/values#`, prefix `kv:`. Version 1.0.0.

This vocabulary says what shape a value has. The core vocabulary says where a fact came from, and a domain ontology says what the fact is about. A domain attribute uses one of these kinds as its range. It does not subclass them.

Source: [`src/knowledge_store/ontology/domain/values.ttl`](../src/knowledge_store/ontology/domain/values.ttl).

| Kind | Range | Stored form | Aligned to |
|---|---|---|---|
| Point in time, a day | `xsd:date` | `2023-07-14` | XML Schema, ISO 8601 |
| Point in time, with a clock | `xsd:dateTime` | `2023-07-14T15:30` or `2023-07-14T15:30Z` | XML Schema, ISO 8601. This is not a date. |
| Duration | `xsd:duration` | `PT2H`, `P3D`, `P2W` | XML Schema, ISO 8601, OWL-Time duration |
| Interval | `kv:interval` | `2023-07-14/2023-07-20`, `09:00/17:00`, `PT2H/PT4H` | ISO 8601 time interval, OWL-Time interval |
| Quantity | `xsd:decimal` or `xsd:integer`, plus `kv:unit` | `1200.5` | The unit is a QUDT IRI when one is exact |

`kv:unit` is an annotation on the attribute, so every value of that attribute shares the unit. A metric stays a metric: it is a query, and it already carries its own unit.

A quarter, a fiscal year, a half, a bare year and a business day stay strings. The calendar they use is not fixed, so they are not these kinds.
