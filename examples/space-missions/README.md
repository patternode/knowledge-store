# Space Missions Sample Corpus

This folder is an original sample corpus written for demonstrating Knowledge Store
ontology-discovery and knowledge-graph tool. The documents were written from scratch for this
demo, in a mix of Markdown, HTML, plain text, and JSON, and deliberately reuse entities
(agencies, launch vehicles, launch sites, planets, and so on) under varying names so that
entity resolution, aliasing, and cross-document linking have something real to work with.

Two invented CSV files sit beside those documents as the structured half of the same
collection. They are the fixture for structured lookup
([docs/architecture/aws/structured.md](../../docs/architecture/aws/structured.md)). The mapping names
them, so refine and extract skip those files and they stay tables. Upload `tables/` with the
documents. A CSV the mapping does not name is still read as prose. The invented costs never
become passages. A question that asks the catalog cites the cell.

## Tables

| Path | Kind | How an answer cites it |
|---|---|---|
| `moon/`, `mars/`, `outer-planets/`, and the other document folders | Prose and JSON the corpus already had | A passage id and a quote copied from that file |
| `tables/missions.csv` | One row per mission | A cell: source, snapshot, table, key, column |
| `tables/launch_vehicles.csv` | One row per rocket | A cell, same shape |

`vehicle_id` on a mission row is the key of a launch-vehicle row, which is the relation
`launchedOn`. Launch vehicle and date also appear in the prose, often under a shorter name
("an Atlas V rocket" in the Juno document, `Atlas V 551` in the vehicle table). The column
`sample_cost_million_usd` appears only in the catalog. Those figures are round numbers made up
for this example. They are not real budgets.

`atlas_v_launches` counts rows whose `vehicle_family` is `Atlas V`: Curiosity, Perseverance,
OSIRIS-REx, Juno, and New Horizons, which is 5.

Which rocket launched Juno, and what sample cost does the catalog give it?

| Claim | Citation | Where the checker looks |
|---|---|---|
| Juno launched on an Atlas V | `p:<passage of outer-planets/juno.json>` plus a quote copied from that file | The Juno document |
| The catalog's vehicle for `juno` is `atlas-v-551`, named Atlas V 551 | `c:missions-tables/<snapshot>/missions/juno/vehicle_id` and `c:missions-tables/<snapshot>/launch_vehicles/atlas-v-551/name` | The two CSVs |
| The sample cost is 1100 | `c:missions-tables/<snapshot>/missions/juno/sample_cost_million_usd` | `missions.csv` only. The prose has no cost |

The mapping, the ontology, the OSI metric file, and the generated R2RML rendition are in
[`ontology/`](ontology). `logical_table` stays `missions` if the catalog later moves to a live
database: replace `location` with `coa:<dataSourceId>` and import
[`ontology/metrics.osi.yaml`](ontology/metrics.osi.yaml) unchanged.

## Sample questions

[`profile.json`](profile.json) is the collection profile. When this collection is selected, the
chat lists these questions. Choosing one fills the box. The cost question also links to
[`tables/missions.csv`](tables/missions.csv). That link is not part of the question.

| Level | Question |
|---|---|
| Low | Which rocket launched Juno? |
| Low | What sample cost does the catalog give Juno? ([missions.csv](tables/missions.csv)) |
| Medium | Which missions launched on an Atlas V? |
| High | Which launched first, Voyager 1 or Voyager 2? |

Set the profile on the collection (the `example_questions` in `profile.json` are the list, including
the markdown link, which Terraform accepts as a string):

```hcl
collections = {
  missions = {
    # Copy examples/space-missions/ontology here. mappings.yaml turns structured lookup on
    # for this collection. Upload the corpus, including tables/, to landing/missions/.
    ontology_dir = "ontology/missions"
    profile = {
      name        = "Space missions"
      description = "Missions, launch vehicles and what the documents say about them."
      example_questions = [
        "[low] Which rocket launched Juno?",
        "[low] What sample cost does the catalog give Juno? [missions.csv](https://github.com/patternode/knowledge-store/blob/main/examples/space-missions/tables/missions.csv)",
        "[medium] Which missions launched on an Atlas V?",
        "[high] Which launched first, Voyager 1 or Voyager 2?",
      ]
    }
  }
}
```

## License

This corpus is dedicated to the public domain under CC0. You may copy, modify, and redistribute
it for any purpose, including commercial use, without attribution.

## Caution

These documents were written from general knowledge, for demonstration purposes, and have not
been fact-checked against primary sources. They may contain errors, omissions, or
simplifications. Do not cite this corpus as a source for any mission's actual history; consult
the relevant space agency's own materials instead. The figures in
`tables/missions.csv` under `sample_cost_million_usd` are invented for the table example.
