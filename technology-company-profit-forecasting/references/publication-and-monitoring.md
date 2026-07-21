# Live Publication and Monitoring

Publication is the final state transition of a current-company forecast.
Current evidence may enter the research and model bundles until the publisher
freezes them; the resulting publication timestamp records that transition.

## One publication entrypoint

Use `scripts/publish_live_forecast.py --workspace <case>`.  Do not hand-author a
live seal or edit publication hashes.  The publisher:

1. resolves active artifacts from the canonical artifact registry and the
   case-selected materiality routes;
2. computes separate evidence, operating-model and financial-forecast bundle
   hashes from registry stage ownership;
3. writes publication metadata into the candidate snapshot;
4. requires strict delivery validation against that exact input pack;
5. recomputes the bundles to detect drift during validation; and
6. writes `forecast_seal.json` last by atomic rename.

Only a valid seal marks a forecast published.  A candidate snapshot or
validation receipt without a seal remains a draft.  Once a valid seal exists,
the workspace is immutable.

## Versioning rather than mutation

A material evidence or model change uses a new workspace and forecast ID.  When
the new publication replaces a prior one, pass `--supersedes-workspace`; the
publisher verifies the prior seal and copies its forecast ID, frozen time and
pack hash into the new publication.  It never guesses the prior version.

## Executable monitoring

Every decisive driver monitor names the exact model node or cell, source or
measurement, expected date/frequency, last observed value, trigger and action.
An upgrade or kill trigger opens a new evidence request and, when material,
creates a new forecast version.  Monitoring never rewrites a published pack in
place.
