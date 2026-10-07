# Ontologies

One directory per collection, holding the master that people edit and release:

```
ontology/
  <collection id>/
    ontology.ttl      # the master: OWL, with owl:versionInfo set to the version it will be
    shapes.ttl        # optional SHACL; generated from the ontology when absent
```

A collection gets its first ontology one of two ways.

## Bring one

Put the ontology here and point the collection at it in `main.tf`:

```hcl
collections = {
  earnings = { ontology_dir = "ontology/earnings" }
}
```

`terraform apply` uploads it, and the next sweep publishes it as the version its `owl:versionInfo`
names, activates it, and extracts against it. Discovery never runs for that collection. To change
the ontology, edit it, bump `owl:versionInfo`, commit and apply: the bump decides what it costs (a
patch re-extracts nothing, a minor extracts only the new terms, a major re-extracts everything). A
file that changed while its version did not is refused, and the collection's status says why.

## Discover one, then change it

Leave `ontology_dir` unset. Once enough documents are refined, the sweep samples them, proposes an
ontology on several samples, consolidates it, and reviews it (a second pass that adds hierarchy,
merges near-duplicates and fixes domains, ranges and datatypes; the draft's report lists every
edit). With `ontology_mode = "curated"` (the default) it stops there with a draft; with `"auto"` it
publishes the draft as 0.1.0 and extracts straight away.

To make the draft your own, pull it here, change it, and either publish it or hand it to Terraform:

```bash
export LAKE_URI=s3://<lake bucket>            # terraform output lake_bucket
knowledge-store -c <collection id> ontology pull <draft id> ontology/<collection id>/
# edit ontology/<collection id>/ontology.ttl; set owl:versionInfo (and owl:versionIRI) to "1.0.0"
knowledge-store -c <collection id> ontology diff ontology/<collection id>/
knowledge-store -c <collection id> ontology publish ontology/<collection id>/ --activate
#   or: set ontology_dir = "ontology/<collection id>" in main.tf, commit and apply
```

Git holds the history of each master; the lake holds each published version, immutable. Later
versions start from `knowledge-store -c <collection id> candidates --propose`, which drafts the
next version from the terms extraction found missing.
