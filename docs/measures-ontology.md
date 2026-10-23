# Knowledge Store measures

Namespace `https://w3id.org/knowledge-store/measures#`, prefix `km:`. Version 1.0.0.

This is the ontology a domain ontology is built from. It has four classes. A domain ontology imports it and adds the things the documents are about. Those things point at a quantity, an instant or a period.

Source: [`src/knowledge_store/ontology/domain/measures.ttl`](../src/knowledge_store/ontology/domain/measures.ttl).

| Class | Meaning | Aligned to |
|---|---|---|
| `km:Metric` | A defined measure. Revenue is a metric. 1200 USD is not. | QUDT quantity kind |
| `km:Quantity` | One number, one unit, one metric. | QUDT quantity |
| `km:Instant` | A point in time. A day and a clock time are different values. | OWL-Time instant |
| `km:Period` | A stretch of time, with a start and end, a duration, or both. | OWL-Time interval |

| Property | From, to | Meaning |
|---|---|---|
| `km:valueOf` | Quantity, Metric | The metric this number is a value of |
| `km:numericValue` | Quantity, decimal | The number, without its unit |
| `km:unit` | Quantity, anyURI | The unit. A QUDT unit IRI when one is exact |
| `km:during` | Quantity, Period | The period the quantity holds over |
| `km:at` | Quantity, Instant | The instant the quantity is stated at |
| `km:onDate` | Instant, date | The calendar day, when no clock is stated |
| `km:atTime` | Instant, dateTime | The instant with a clock |
| `km:beginning` | Period, Instant | When the period starts |
| `km:end` | Period, Instant | When the period ends |
| `km:duration` | Period, duration | How long it lasts, such as `P10Y` or `PT2H` |
| `km:interval` | Period, interval | The same stretch as one `start/end` literal |

The alignment is `rdfs:seeAlso`. The terms are written here so a collection can use them without loading the QUDT or OWL-Time graphs.

## How a domain ontology uses it

Import `https://w3id.org/knowledge-store/measures` and add classes for what the documents are about. A price, a reading or a reported figure is a relation to `km:Quantity`. A launch day or a deadline is a relation to `km:Instant`. A cruise, a subscription or a reporting window is a relation to `km:Period`.

An attribute still carries a value kind when every value of that attribute has the same shape. A launch date that is always a day is an `xsd:date`. A cost that is always US dollars is a decimal with `kv:unit`. Use a quantity when the metric or the unit varies from one value to the next, or when the number belongs to a period.

A domain class does not subclass `km:Quantity` or `km:Instant` to mean that the thing is a number or a time. A company is a company. Its revenue is a quantity of a metric during a period.

A quarter, a fiscal year, a half or a bare year stays a string until the documents give it a start and an end. Then it is a period.

## Versioning

The measures ontology is versioned on its own, as the core vocabulary is. Additions are minor. A change to the meaning of a term, or its removal, is major. The version IRI is `https://w3id.org/knowledge-store/measures/1.0.0`.
