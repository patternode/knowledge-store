# Sherlock Holmes sample

Two kinds of source, one collection. The short stories are prose. A small catalog of the same
stories is CSV. A question can cite both: a passage from a story, and a cell from a table.

This is the fixture for the structured-lookup draft
([docs/architectures/structured.md](../../docs/architectures/structured.md)). The sweep today
still parses a CSV as text. Nothing here binds a column or checks a cell yet.

The stories are not in this repository. `fetch.py` downloads three public-domain collections
from Project Gutenberg, strips the Project Gutenberg header and footer, and writes one file
per story under `stories/`. The catalog below was written for this demo.

## What sits in the source

| Path | Kind | How an answer cites it |
|---|---|---|
| `stories/<book>/<nn>-<slug>.txt` | Document. One story, from `fetch.py` | A passage id and a quote copied from that file |
| `tables/stories.csv` | Table. One row per story | A cell: source, snapshot, table, key, column |
| `tables/strand_issues.csv` | Table. One row per Strand issue | A cell, same shape |

The story text does not say which issue of The Strand Magazine it appeared in. The catalog
does not contain the scene. That split is the point.

```
landing/holmes/
  stories/the-adventures-of-sherlock-holmes/08-the-adventure-of-the-speckled-band.txt
  tables/stories.csv
  tables/strand_issues.csv
```

Upload both trees to `landing/<collection>/`. The ontology and the mapping are published, not
uploaded as documents: [`ontology/`](ontology).

A CSV named in [`ontology/mappings.yaml`](ontology/mappings.yaml) is bound as a table. Its
snapshot is the sha256 of the file. It is not refined and not extracted. Any other file,
including a CSV the mapping does not name, stays on the document path.

## The catalog

`stories.csv` holds four stories. `strand_issues.csv` holds the issue each one first appeared
in. `strand_issue` in the story row is the key of the issue row, which is the relation
`publishedIn` in the ontology.

| story_id | client | strand_issue |
|---|---|---|
| scandal-in-bohemia | Wilhelm Gottsreich Sigismond von Ormstein | 1891-07 |
| red-headed-league | Jabez Wilson | 1891-08 |
| blue-carbuncle | Peterson | 1892-01 |
| speckled-band | Helen Stoner | 1892-02 |

These dates and labels are a demonstration catalog, written from general knowledge. Check a
bibliography before relying on one. Peterson is recorded as the client of the blue carbuncle
because he is the person who brings Holmes the hat and the goose.

## A question that cites both

When did The Strand Magazine publish the story in which Helen Stoner comes to Holmes, and how
many of the catalogued stories had already appeared in 1891?

| Claim | Citation | Where the checker looks |
|---|---|---|
| Helen Stoner asks Holmes to look into her sister's death | `p:<passage of 08-the-adventure-of-the-speckled-band.txt>` plus a quote copied from that passage | The fetched story |
| The catalog's client for `speckled-band` is Helen Stoner | `c:holmes-tables/<snapshot>/stories/speckled-band/client` | `stories.csv`, that row, column `client` |
| That story's issue is `1892-02` | `c:holmes-tables/<snapshot>/stories/speckled-band/strand_issue` | `stories.csv`, column `strand_issue` |
| Issue `1892-02` is The Strand Magazine, February 1892 | `c:holmes-tables/<snapshot>/strand_issues/1892-02/year` and `.../month` and `.../magazine` | `strand_issues.csv` |
| Two catalogued stories first appeared in 1891 | `m:strand_stories_1891/<snapshot>` | Recompute `SELECT COUNT(*) FROM stories WHERE strand_issue LIKE '1891-%'`, which is 2 |

The passage quote has to occur in the story. Each cell value has to equal the CSV cell. The
count has to equal the recomputed figure. A claim that only says "February 1892" with a quote
from the story fails, because the story file does not contain the issue.

## What was taken from Context Ontology Accelerator

Two files, both already the accelerator's own formats, and nothing that runs its stack.

[`ontology/r2rml-mapping.ttl`](ontology/r2rml-mapping.ttl) is the rendition of the mapping.
The accelerator generates this shape when it maps a table: one triples map per table, the key
as an IRI template, a column as a predicate, a foreign key as a join. Ontop is what executes
it against a live database. This sample only shows the file.

[`ontology/metrics.osi.yaml`](ontology/metrics.osi.yaml) is an OSI v1.0 metric file with a
`custom_extensions` entry of `vendor_name: COA`, the same shape as
`packages/metric-service/examples/sample-osi-import.yaml` in the accelerator. The expression
is a complete read-only `SELECT`. Locally the checker recomputes it from the snapshot. Later,
`POST /namespaces/{ns}/import-osi` loads this file unchanged, provided the approved source has
a table named `stories`.

`data_source_id: holmes-tables` is the lake source in this example. When the catalog moves to
a live database, that id becomes the accelerator's data source id. `logical_table` in the
mapping, `rr:tableName` in the rendition, and `source_table` on the metric stay `stories`.

Left for that later step: the accelerator's source scan, ontology induction, Ontop service,
natural-language SQL, Cedar policies, and the MCP `query` tool. The Holmes agent still calls
fixed tools, and a live result is usable only when it carries cells this checker can re-read.
