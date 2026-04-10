# Lakehouse Unification Plan

  ## Summary

  Unify all active data and process paths around a single canonical lakehouse:

  - Canonical warehouse and bucket: gs://novagrid-lakehouse
  - Canonical contract authority: phoenix_lakehouse, consumed as a pinned dependency or pinned config source, not as an
    uncontrolled runtime fallback
  - Canonical ingestion/backfill path: data_pipeline/cenace_workers
  - Legacy buckets:
      - lakehouse_phoenix = frozen parquet archive and migration source
      - novogrid-workqueue = frozen legacy bucket, no active writes

  The main goal is to eliminate silent drift between repos by making one authority for contracts and one authority for
  storage location, while preserving enough compatibility to migrate existing data safely.

  ## Key Changes

  ### 1. Contract authority and config discipline

  - Keep phoenix_lakehouse as the single source of truth for lakehouse config, table contracts, identifiers, and path
    conventions.
  - Change consuming repos to use a pinned phoenix_lakehouse version or pinned local editable install in development.
  - Remove normal-operation fallback behavior as a primary mechanism in active paths.
  - Allow checked-in snapshots only as explicit emergency/bootstrap artifacts for isolated worker deployment, never as equal
    peers to the canonical contract source.
  - Add one documented contract sync rule:
      - contract changes happen in phoenix_lakehouse
      - consumers upgrade intentionally
      - any baked snapshot must be regenerated from that pinned contract revision and annotated with the source revision
  - Document a release and pin policy so “pinned” is actionable:
      - cut phoenix_lakehouse releases with immutable tags or versioned packages (semver or date-based), whichever the org
        standardizes on
      - consumer repos record the pin in lockfiles or explicit dependency constraints, not only “latest” in an environment
      - upgrades are deliberate: bump pin, regenerate worker snapshots from that revision, run contract resolution tests

  ### 2. Storage model and naming cleanup

  - Treat novagrid-lakehouse as the only active lakehouse bucket across novagrid, data_pipeline, and novafront.
  - Rename internal terminology in docs/config/comments so “lakehouse” always means novagrid-lakehouse.
  - Reclassify:
      - lakehouse_phoenix as legacy_parquet_archive
      - novogrid-workqueue as legacy_workqueue_archive
  - Remove active-code references that imply either legacy bucket is valid for new writes.
  - Preserve legacy bucket readers only in explicit migration or archive tooling, not in default runtime codepaths.
  - One active Iceberg catalog for canonical tables: document a single catalog URI / REST / HMS configuration and avoid
    parallel catalogs that could register the same namespaces or tables differently (split-brain risk).
  - Ensure IAM and workload identity: every service account or runtime that writes or reads the canonical warehouse has
    explicitly documented roles on gs://novagrid-lakehouse (and catalog backend if separate); validate in staging before
    cutover.

  ### 3. data_pipeline process consolidation

  - Make cenace_workers the documented and supported ingestion/backfill implementation.
  - Before treating Prefect flows and pipeline_tasks as legacy, run a one-time inventory: scheduled Prefect jobs, on-call
    runbooks, secrets/envs, and every production entrypoint still invoking old orchestration. Document explicit exceptions
    for any workflow that must stay; everything else becomes legacy compatibility code.
  - Update worker config and any active backfill scripts so all new writes target novagrid-lakehouse.
  - Keep migration helpers for reading lakehouse_phoenix and novogrid-workqueue, but isolate them under migration/archive
    commands.
  - Standardize one ingestion lifecycle:
      - extract or consolidate locally/on worker
      - write bronze into novagrid-lakehouse
      - update Iceberg catalog in the canonical warehouse
      - optionally run maintenance/compaction
  - Remove ambiguity between “parquet bronze contract bucket” and “Iceberg warehouse bucket” by making them the same
    canonical destination.

  ### 4. novagrid and novafront alignment

  - Keep novafront on novagrid-lakehouse; it is already aligned and should become the reference consumer.
  - Update novagrid active config so it no longer points at stale or conflicting bucket assumptions.
  - Standardize novagrid reads on the canonical contract and canonical warehouse.
  - If direct parquet reads are still needed temporarily, scope them explicitly as compatibility reads against canonical
    novagrid-lakehouse paths only.
  - Remove or rewrite any bundled novagrid config that still treats lakehouse_phoenix as the expected analytics location.

  ### 5. Migration and compatibility handling

  - Freeze all new writes to lakehouse_phoenix and novogrid-workqueue first.
  - Inventory which datasets in each legacy bucket are still needed by active consumers.
  - Legacy bucket sizing (reference for migration planning; `gcloud storage du -s gs://lakehouse_phoenix` once showed on the
    order of ~7 GiB object usage—re-run before large transfers).
  - Migrate required data into novagrid-lakehouse with clear mapping:
      - lakehouse_phoenix parquet paths map into canonical bronze/silver/gold or reference areas
      - novogrid-workqueue data is imported only if still needed for product or modeling workflows
  - Maintain read-only migration tooling until parity is confirmed.
  - After parity:
      - remove active code references to legacy buckets
      - keep only archive/migration documentation
      - defer physical bucket cleanup until post-validation

  ## Interfaces and behavior

  - Public bucket constants/configs in active repos must resolve to novagrid-lakehouse.
  - Any contract-loading API in consuming repos must prefer pinned phoenix_lakehouse and fail loudly if canonical contracts
    are unavailable in supported environments—except documented bootstrap paths (isolated workers, air-gapped deploys) that
    load a labeled snapshot generated from a known phoenix_lakehouse revision; those paths must not silently override pins in
    normal CI or production.
  - Worker/bootstrap snapshots may remain, but they must be explicitly labeled generated artifacts with source revision
    metadata.
  - Active CLI/help text should describe one supported backfill path: cenace_workers.

  ## Rollout sequencing

  Coordinate cross-repo changes to avoid mixed-bucket deploys:

  - Publish a phoenix_lakehouse release (tag/package) with any contract or path updates needed for the canonical bucket.
  - Point data_pipeline/cenace_workers and other writers at the new pin and gs://novagrid-lakehouse; deploy writers before or
    with readers.
  - Bump novagrid and novafront to the same contract pin and confirm reads resolve to novagrid-lakehouse.
  - Run migration/read-only parity checks on legacy buckets; only then remove active references to legacy write paths.
  - Order can be adjusted per environment, but the invariant is: no long-lived state where some services write the canonical
    path and others still assume legacy paths without an explicit compatibility window.

  ## Test Plan

  - Contract resolution tests:
      - consumer repos load canonical contracts from pinned phoenix_lakehouse
      - generated worker snapshot matches pinned contract revision
  - Storage target tests:
      - active write paths in cenace_workers resolve to gs://novagrid-lakehouse/...
      - active novagrid read paths resolve to novagrid-lakehouse
      - novafront browse/query paths continue to use novagrid-lakehouse
      - canonical Iceberg catalog configuration resolves to the single documented catalog (no duplicate registry of the same
        table identifiers)
  - Regression scans:
      - no active codepaths reference lakehouse_phoenix or novogrid-workqueue for new writes
      - remaining references are limited to migration/archive tooling and legacy docs
  - End-to-end scenarios:
      - run a representative backfill/write through cenace_workers
      - verify bronze table/catalog visibility in novagrid-lakehouse
      - verify novafront can browse/query resulting datasets
      - verify novagrid analytics/modeling can read the canonical data source
  - Migration validation:
      - compare sample dataset counts and partition coverage between legacy source and migrated canonical destination
      - verify no active consumer still depends on legacy buckets after cutover
  - Access sanity checks (staging or dry-run):
      - writer identity used by cenace_workers can create/update objects under the expected novagrid-lakehouse prefixes
      - reader identities used by novagrid and novafront can list and read the same canonical prefixes they need

  ## Assumptions and defaults

  - phoenix_lakehouse remains the authority, but consumers use it through pinned versions rather than unbounded dynamic
    drift.
  - cenace_workers is the primary supported ingestion/backfill path.
  - lakehouse_phoenix and novogrid-workqueue are frozen first, then migrated selectively.
  - novafront is already correctly aligned and should not be structurally changed beyond config cleanup and consistency
    checks.
  - Prefect-era orchestration remains legacy after the dependency inventory in Key Changes §3; anything still required is
    listed explicitly rather than discovered during cutover.