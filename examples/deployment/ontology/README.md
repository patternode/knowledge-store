# Curated ontologies

One directory per collection, holding the master that people edit and release:

```
ontology/
  <collection id>/
    ontology.ttl      # the master: OWL, with owl:versionInfo set to the version it will be
```

The first draft comes from discovery. Pull it, curate it here, and publish it:

```bash
export LAKE_URI=s3://<lake bucket>            # terraform output lake_bucket
knowledge-store -c <collection id> ontology pull <draft id> ontology/<collection id>/
# edit ontology/<collection id>/ontology.ttl, set owl:versionInfo "1.0.0", commit it
knowledge-store -c <collection id> ontology diff ontology/<collection id>/
knowledge-store -c <collection id> ontology publish ontology/<collection id>/ --activate
```

Git holds the history of each master; the lake holds each published version, immutable. Later
versions start from `knowledge-store -c <collection id> candidates --propose`, which drafts the
next version from the terms extraction found missing.
