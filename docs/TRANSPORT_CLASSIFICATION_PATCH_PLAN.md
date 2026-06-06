# Transport Classification Patch and Enhancement Plan

## Status

Proposed implementation plan based on the repository state audited on 2026-06-06.

## Problem Statement

The current UI label treats `API capability`, `IP/network dependency`, and `physical bearer` as one binary property:

- `網路 / API（有線）`
- `非網路 / 實體媒介`

These are not mutually exclusive technical dimensions. A product can expose an API while its device-side bearer is cellular, satellite, Wi-Fi, or another wireless medium. It can also be a wired technology without using Ethernet or an API.

Example:

- `1NCE IoT eSIM` exposes management APIs.
- Its device bearer is cellular/eSIM, not Ethernet cable.
- The current label `網路 / API（有線）` is therefore materially misleading.
- The correct presentation should separate bearer from control capability, for example:
  - Primary: `蜂巢 / eSIM（無線）`
  - Capability: `API 管理`
  - Network dependency: `IP 網路`

## Audit Findings

### 1. Backend classifier collapses independent dimensions

`rag_engine/src/worker.js` currently returns only:

- `network_api_wired`
- `non_network_physical`

The `network_api_wired` branch is selected when text contains terms such as `api`, `cloud`, `voice`, `sip`, or `ip`. None of those terms proves that the device-side transport is wired.

Applying the current function to `frontend/data/solution_registry.json` produces:

| Current classification | Count |
|---|---:|
| `network_api_wired` | 156 |
| `non_network_physical` | 0 |

This means the current classification does not discriminate among any solution records.

### 2. Frontend fallback labels every solution as wired/API

`frontend/app/tech-alternatives/page.jsx` returns `網路 / API（有線）` whenever a solution does not already include a cloud-provided transport label. The local solution registry does not contain `transport_type`, so every solution card receives the wired/API label before or without a RAG request.

### 3. Known cellular/eSIM false positives

Seven solution records have cellular/eSIM tags but currently display as wired:

- Twilio Super SIM / IoT SIM
- 1NCE IoT eSIM
- emnify IoT eSIM
- SORACOM Air for Cellular
- KORE OmniSIM
- Eseye AnyNet+ eSIM
- Hologram Hyper SIM

Six of these also carry an `api` tag. API capability must be rendered as a separate capability badge, not used to infer a cable.

### 4. Analog and hybrid products are also mislabeled

Twenty-eight solution rows contain one or more analog/TDM/FXS/FXO tags. They are currently labeled `網路 / API（有線）`, including legacy TDM products that may expose no API at all.

Examples:

- Panasonic KX-TDA/TDE
- Toshiba Strata CIX
- Panasonic KX-TA series
- Nortel BCM / CS1000
- Ericsson MD110

Hybrid products need multiple bearer values or an explicit `hybrid` designation rather than being forced into a single API bucket.

### 5. Alternative `category` is not a bearer taxonomy

The alternatives catalog has 131 records:

| Existing category | Count |
|---|---:|
| `web` | 53 |
| `non_web` | 78 |

The `non_web` category currently includes all of the following:

- 29 wired non-IP methods, such as RS-485, fieldbus, USB, dry contact, and powerline.
- 20 wireless non-IP or signaling methods, such as sub-GHz radio, DECT, paging, and near-field methods.
- 16 physical, optical, acoustic, mechanical, or manual methods.
- 8 wireless IP/carrier records.

The `web` category also contains cellular IP and virtual/edge-compute options. Therefore `web` cannot mean wired and `non_web` cannot mean physical.

### 6. Filtering and exclusion logic use different mental models

The backend exclusion logic already recognizes cellular/eSIM/satellite as allowed bearers that can rescue a solution when Ethernet is forbidden. The display classifier then discards that distinction and labels the same row as wired/API.

The browser also duplicates a simpler exclusion parser. This creates drift between:

- catalog generation,
- backend eligibility filtering,
- backend display classification,
- frontend fallback classification,
- frontend category filtering.

## Target Model

Replace the binary transport label with a normalized, multidimensional classification object.

### Canonical schema

```json
{
  "transport": {
    "primary_bearer": "cellular_esim",
    "bearer_family": "cellular",
    "link_mode": "wireless",
    "network_type": "ip",
    "internet_dependency": "provider_managed",
    "bearers": ["cellular_esim"],
    "control_interfaces": ["api"],
    "api_capable": true,
    "hybrid": false,
    "confidence": "explicit",
    "classification_source": "catalog"
  }
}
```

### Required dimensions

#### `bearer_family`

Allowed initial values:

- `ethernet`
- `cellular`
- `wifi`
- `radio`
- `satellite`
- `serial`
- `fieldbus`
- `powerline`
- `electrical_contact`
- `usb_local_bus`
- `optical`
- `acoustic`
- `mechanical`
- `visual_code`
- `manual_process`
- `cloud_or_platform`
- `unknown`

#### `link_mode`

- `wired`
- `wireless`
- `contactless`
- `physical`
- `manual`
- `virtual`
- `hybrid`
- `unknown`

#### `network_type`

- `ip`
- `non_ip_digital`
- `analog`
- `physical_signal`
- `manual`
- `mixed`
- `unknown`

#### `control_interfaces`

Multi-value capability list, not a transport:

- `api`
- `webhook`
- `sip`
- `messaging`
- `graphql`
- `rest`
- `gpio`
- `relay`
- `serial_protocol`
- `fieldbus_protocol`
- `manual`
- other normalized protocol families

#### Classification quality

- `confidence`: `explicit`, `derived`, or `unknown`
- `classification_source`: `catalog`, `tag_rule`, `medium_rule`, or `fallback`

The UI should visibly identify `unknown` or derived classifications rather than inventing a wired bearer.

## Display Model

### Primary badge: actual bearer

Examples:

| Record | Primary badge |
|---|---|
| 1NCE IoT eSIM | `蜂巢 / eSIM（無線）` |
| SIP over Ethernet gateway | `乙太網路 / IP（有線）` |
| Wi-Fi control | `Wi-Fi / IP（無線）` |
| RS-485 / Modbus RTU | `序列線路（有線、非 IP）` |
| Dry Contact / Relay Closure | `乾接點 / 繼電器（實體有線）` |
| LoRaWAN | `LPWAN 無線電（無線）` |
| Satellite command | `衛星（無線）` |
| Cloud platform with no bearer evidence | `雲端平台（承載未指定）` |

### Secondary capability badges

Examples:

- `API 管理`
- `Webhook`
- `SIP`
- `REST`
- `GPIO`
- `人工操作`

An API badge must never imply `wired`.

### Filtering model

Replace the existing category buttons with independent controls:

1. Link mode:
   - 全部
   - 有線
   - 無線
   - 實體 / 無接觸
   - 人工 / 流程
   - 承載未指定
2. Network type:
   - IP 網路
   - 非 IP 數位
   - 類比
   - 實體訊號
3. Interface/capability:
   - API
   - SIP
   - Webhook
   - GPIO / Relay
   - Serial / Fieldbus

For backward compatibility, a coarse two-way view may remain as an optional grouping, but it must not include `(有線)` in a group defined by API capability.

## Source-of-Truth Changes

### 1. Add a shared taxonomy module

Create a canonical taxonomy in Python because the research generators own the source datasets. Suggested file:

`src/research/transport_taxonomy.py`

Responsibilities:

- normalized enums/constants,
- medium-to-bearer mapping,
- tag-to-interface mapping,
- solution classification,
- alternative classification,
- validation and confidence assignment,
- bilingual display-label generation only where presentation-independent.

Do not maintain separate regex taxonomies in Python, Worker JavaScript, and React.

### 2. Enrich solution registry generation

Update `src/research/product_researcher.py` so every generated solution record contains explicit transport fields.

Required behavior:

- Prefer explicit crawler/catalog metadata.
- Map `esim` or `cellular` tags to a wireless cellular bearer.
- Map `satellite` to a wireless satellite bearer.
- Map `tdm`, `analog`, `fxs`, and `fxo` to analog or hybrid bearer evidence.
- Keep `api`, `cpaas`, `webhook`, and similar tags in `control_interfaces`.
- Mark mixed analog/IP appliances as `hybrid` and retain all detected bearers.
- Use `cloud_or_platform` plus `unknown` link mode when no last-mile bearer is stated.

### 3. Enrich alternatives generation

Update `src/research/tech_researcher.py` so `medium` maps to explicit normalized dimensions. Retain `category` temporarily for compatibility, but stop using it as a physical transport label.

### 4. Export enriched data

Update `scripts/generate_research_outputs.py` and generated CSV/JSON schemas to include:

- `primary_bearer`
- `bearer_family`
- `link_mode`
- `network_type`
- `bearers`
- `control_interfaces`
- `api_capable`
- `hybrid`
- `transport_confidence`
- `transport_classification_source`

For CSV output, serialize multi-value fields with a documented delimiter. JSON should use arrays and booleans.

### 5. Update asset synchronization

Update `scripts/sync_rag_assets.py` manifest metric fields and schema validation so enriched fields are included in the RAG asset bundle.

## GitHub Actions, Crawler, and R2 Consistency Plan

### Current workflow behavior

`.github/workflows/report.yml` currently performs these relevant operations:

1. Runs `scripts/generate_research_outputs.py` before notebooks.
2. Commits the resulting `frontend/data/*.json`, processed CSV files, reports, and README summary back to `main`.
3. Runs notebooks, including product research and technology alternatives.
4. Runs `scripts/generate_research_outputs.py` a second time.
5. Builds the RAG manifest from reports, processed data, and frontend data.
6. Uploads every manifest asset to Cloudflare R2 under the `latest/` prefix.
7. Builds the bilingual frontend from the second-pass local files.

This creates a consistency risk: the committed frontend JSON can come from the first generation pass while R2 and GitHub Pages use the second pass. If notebooks, crawler context, or generation behavior changes data, the same Git commit can expose different classifications locally, on Pages, and through R2.

### Required workflow invariant

The following artifacts must be generated from the same classified dataset snapshot and must contain identical normalized transport values for each stable record identity:

- `data/processed/solution_registry.csv`
- `data/processed/awesome_list.csv`
- `frontend/data/solution_registry.json`
- `frontend/data/awesome_list.json`
- generated reports that display transport fields
- `rag_engine/dist/rag_assets_manifest.json`
- objects uploaded to Cloudflare R2
- Hugging Face asset bundle
- files consumed by the bilingual frontend build

No UI component, Worker, R2 manifest builder, or upload step may independently infer a contradictory transport label.

### Authoritative classification boundary

Transport classification must run inside `scripts/generate_research_outputs.py`, through the shared Python taxonomy module, after crawler/notebook data has been merged and immediately before CSV/JSON/report serialization.

The generated normalized fields are authoritative. Downstream systems may translate enum values into localized text or style them, but must not reclassify them.

The flow must become:

```text
crawler + static catalog + notebook outputs
                  |
                  v
       shared transport taxonomy
                  |
                  v
     validate normalized catalog snapshot
                  |
       +----------+-----------+
       |          |           |
       v          v           v
 frontend JSON  processed CSV reports
       |          |           |
       +----------+-----------+
                  |
                  v
      manifest + checksum parity gate
                  |
       +----------+-----------+
       |                      |
       v                      v
 frontend build        R2 / HF publication
```

### `report.yml` patch requirements

1. Do not commit the first-pass generated catalogs before notebooks if notebooks can affect the final dataset.
2. Generate provisional outputs before notebooks only when notebooks require them as input.
3. After notebooks, run one final canonical generation pass.
4. Run `scripts/validate_transport_catalog.py` immediately after the final pass.
5. Commit the final canonical files only after validation succeeds.
6. Build the RAG asset manifest only from those validated files.
7. Run a manifest/catalog parity verifier before any upload.
8. Upload to R2 only after all classification and parity gates pass.
9. Build the frontend from the same validated files used for the manifest.
10. Upload a classification audit artifact for every scheduled or manually dispatched run.

Recommended high-level step order:

```yaml
- Generate provisional research inputs
- Run notebooks / crawler enrichment
- Generate final canonical research outputs
- Validate transport taxonomy and record identities
- Commit final crawler/catalog snapshot
- Build RAG manifest
- Verify manifest and catalog checksums
- Upload validated snapshot to R2
- Build frontend from validated snapshot
- Deploy Pages
```

### Crawler contract

`src/research/solution_crawler.py` currently returns discovered records with tags but no explicit transport object. Update its `DiscoveredSolution` contract to accept transport evidence separately from product capabilities.

Suggested fields:

```python
bearers: tuple[str, ...]
control_interfaces: tuple[str, ...]
transport_evidence: str
transport_source_url: str
```

Requirements:

- `api` remains a control interface, never a bearer.
- `cellular` and `esim` are bearer evidence.
- Cloud/UCaaS/CPaaS entries with no last-mile evidence use `cloud_or_platform` and `unknown` link mode.
- New crawler records must either provide explicit evidence or be marked `unknown` with derived confidence.
- The crawler must not emit localized UI labels.
- Taxonomy validation must reject unrecognized bearer enum values.

### R2 manifest schema v2

`scripts/sync_rag_assets.py` currently summarizes solution transport using the raw `tags` field. That repeats the same conceptual error because tags mix bearer, product category, lifecycle, and capability.

Change `CATALOG_LABEL_FIELDS` to summarize normalized fields instead:

```python
"frontend/data/solution_registry.json": {
    "transport_fields": [
        "primary_bearer",
        "bearer_family",
        "link_mode",
        "network_type",
        "control_interfaces",
    ],
    "schema_version_field": "transport_schema_version",
}
```

Manifest-level requirements:

- Add `transport_schema_version`.
- Add distinct `bearer_families`, `link_modes`, `network_types`, and `control_interfaces` per catalog asset.
- Add catalog content SHA-256 values, already available at asset level, to a dedicated `catalog_snapshot` block.
- Add record counts and stable identity checksum.
- Add validation status and unknown/hybrid counts.
- Remove the claim that solution `tags` are the transport field.

Suggested manifest fragment:

```json
{
  "transport_schema_version": 2,
  "catalog_snapshot": {
    "solution_registry_sha256": "...",
    "awesome_list_sha256": "...",
    "solution_record_count": 156,
    "alternative_record_count": 131,
    "classification_valid": true,
    "unknown_solution_count": 0,
    "unknown_alternative_count": 0
  }
}
```

### Exact UI/R2 logic requirement

“Exact same label logic” must mean:

- R2 stores canonical enum fields and optional centrally generated bilingual display labels.
- The UI reads those fields directly from the same generated JSON snapshot.
- The RAG Worker reads the R2 copy of that snapshot and returns the same fields without reclassification.
- UI localization maps canonical enums to text through one versioned label dictionary.
- A label-dictionary version is included in generated assets when display strings are serialized.

It must not mean copying the same regex implementation into Python, Worker JavaScript, and React. Duplicate implementations will drift as new crawler context is added.

### Atomic R2 publication

Uploading directly into `latest/` object by object can expose a partially updated dataset. Use an immutable run prefix and promote a pointer only after successful upload and verification.

Recommended layout:

```text
snapshots/<github_run_id>/frontend/data/solution_registry.json
snapshots/<github_run_id>/frontend/data/awesome_list.json
snapshots/<github_run_id>/rag_engine/dist/rag_assets_manifest.json
latest-pointer.json
```

Publication sequence:

1. Upload all assets to `snapshots/<github_run_id>/`.
2. Verify remote object size/checksum for both catalogs and manifest.
3. Upload `latest-pointer.json` containing the immutable prefix, schema version, commit SHA, and catalog checksums.
4. Make the Worker resolve the pointer once per request or cache interval.
5. Retain previous snapshots for rollback.

If the current `latest/` layout must remain temporarily, upload catalogs first, manifest last, and make the Worker reject a manifest whose catalog checksums do not match fetched objects. Immutable snapshots are still the preferred final design.

### CI parity verifier

Add `scripts/verify_transport_snapshot.py` with these checks:

- JSON and processed CSV record counts match.
- Stable record identities match across representations.
- Normalized transport fields match across CSV and JSON.
- Generated reports use only recognized label mappings.
- Manifest checksums match local files.
- R2 pair list contains both catalogs and the manifest.
- Frontend build input checksums equal manifest catalog checksums.
- No source contains the deprecated `network_api_wired` value after migration completion.
- No solution with `bearer_family=cellular` has `link_mode=wired` unless explicitly hybrid.

The script should emit a machine-readable report such as:

`rag_engine/dist/transport_snapshot_validation.json`

Upload this report as a workflow artifact and include it in R2 snapshots.

### R2 upload verification

For both Wrangler and S3 upload paths:

- fail on missing source files,
- verify expected object count,
- verify catalog and manifest checksums,
- record Git commit SHA and GitHub run ID,
- do not update the latest pointer after any failed upload,
- preserve the previous latest pointer for rollback.

### Runtime consistency checks

The Worker response evidence should include:

```json
{
  "transport_schema_version": 2,
  "catalog_snapshot_id": "<github-run-id-or-sha>",
  "catalog_manifest_sha256": "...",
  "label_dictionary_version": 2
}
```

The frontend may log or display these values in a diagnostics area. This makes a stale frontend/R2 mismatch observable instead of silently displaying conflicting labels.

## Backend Patch Plan

### `rag_engine/src/worker.js`

1. Remove `network_api_wired` as a canonical transport type.
2. Read explicit transport fields from catalog rows first.
3. Add a compatibility derivation only for old payloads.
4. Keep API/control interfaces separate from bearer classification.
5. Return the normalized transport object in both ranked arrays and table rows.
6. Return preformatted display labels as convenience fields, but keep raw normalized fields authoritative.
7. Change exclusions to compare against normalized bearer/network dimensions.
8. Preserve multi-bearer rows when at least one allowed deployment path remains, and report which path survived.
9. Add evidence fields showing excluded and retained bearer paths.

Suggested response fragment:

```json
{
  "name": "1NCE IoT eSIM",
  "transport": {
    "primary_bearer": "cellular_esim",
    "bearer_family": "cellular",
    "link_mode": "wireless",
    "network_type": "ip",
    "control_interfaces": ["api"],
    "api_capable": true
  },
  "transport_label": "蜂巢 / eSIM（無線）",
  "capability_labels": ["API 管理"]
}
```

### Compatibility behavior

During one response-version transition:

- Continue returning `transport_label`.
- Add `transport_schema_version: 2`.
- Treat old `transport_type` as deprecated.
- Do not map unknown rows to wired; use `unknown` / `承載未指定`.

## Frontend Patch Plan

### `frontend/app/tech-alternatives/page.jsx`

1. Normalize schema-v2 transport objects.
2. For legacy responses, classify from catalog-enriched fields before applying any heuristic.
3. Remove the default that labels missing data as wired/API.
4. Render one bearer badge plus zero or more capability badges.
5. Replace `transportClass()` with style mapping based on `link_mode` and `network_type`.
6. Replace `cloudCategory()` with independent filter predicates.
7. Show `承載未指定` for platform-only solutions.
8. Display hybrid solutions with either `混合承載` or multiple bearer badges.
9. Add a compact explanation/tooltip for derived classifications.
10. Ensure the RAG table and solution cards use the same normalized rendering component.

### Component extraction

Introduce reusable components, for example:

- `TransportBadges`
- `TransportFilters`
- `ClassificationConfidence`

This avoids card/table disagreement and keeps bilingual labels centralized.

### CSS

Replace binary `.network` and `.non-network` styles with semantic styles:

- `.transport-wired-ip`
- `.transport-wireless-ip`
- `.transport-wired-non-ip`
- `.transport-physical`
- `.transport-manual`
- `.transport-unknown`
- `.capability-api`

Colors must not be the only distinction; each badge must contain explicit text.

## Data Migration Strategy

### Phase 1: taxonomy and validation

- Implement the shared taxonomy module.
- Add unit tests using a fixed classification fixture matrix.
- Generate an audit report listing every record, assigned dimensions, confidence, and rule source.
- Fail generation if a known medium maps to `unknown`.

### Phase 2: regenerate datasets

- Regenerate `data/processed/solution_registry.csv`.
- Regenerate `data/processed/awesome_list.csv`.
- Regenerate frontend JSON assets.
- Review all `unknown` and `hybrid` rows manually.

### Phase 3: backend schema v2

- Add explicit transport objects and table fields.
- Retain deprecated compatibility fields temporarily.
- Update RAG prompt context to distinguish API interface from bearer.

### Phase 4: frontend migration

- Render schema-v2 fields.
- Add independent filters.
- Remove binary fallback logic.
- Verify desktop and mobile layouts with realistic long Chinese labels.

### Phase 5: remove legacy taxonomy

- Remove `web`/`non_web` as a display taxonomy.
- Remove deprecated `transport_type` after all deployments use schema v2.
- Keep old fields only if required for historical report compatibility.

## Test Plan

### Taxonomy unit-test matrix

At minimum, assert:

| Input | Expected bearer | Link mode | Network type | Capability |
|---|---|---|---|---|
| 1NCE IoT eSIM | cellular/eSIM | wireless | IP | API |
| Twilio Super SIM | cellular/eSIM | wireless | IP | API |
| Ethernet REST API | Ethernet | wired | IP | REST/API |
| Wi-Fi device API | Wi-Fi | wireless | IP | API |
| RS-485 Modbus | serial | wired | non-IP digital | serial protocol |
| Dry contact relay | electrical contact | wired/physical | physical signal | relay/GPIO |
| LoRaWAN | radio/LPWAN | wireless | IP or non-IP per catalog definition | messaging |
| Satellite command | satellite | wireless | IP/provider dependent | protocol/API as present |
| Panasonic KX-TDA/TDE | analog/TDM | wired | analog | none unless explicit |
| Hybrid IP PBX with FXS | multiple | hybrid | mixed | SIP plus analog |
| Cloud service without bearer data | cloud/platform | unknown | IP platform | API if explicit |

### Backend tests

- No cellular/eSIM row may return a wired link mode.
- An API tag must not change `link_mode`.
- No missing transport evidence may default to wired.
- Ethernet exclusions must not remove allowed cellular paths.
- Wireless exclusions must remove cellular/Wi-Fi/radio as specified.
- Hybrid rows must expose retained and excluded paths correctly.
- Response table and ranked arrays must carry identical transport data.

### Frontend tests

- 1NCE renders `蜂巢 / eSIM（無線）` and `API 管理` as separate badges.
- Category filters operate independently by link mode and capability.
- Local cards and cloud RAG table show identical badges for the same product.
- Unknown bearer renders `承載未指定`, not wired.
- Long Chinese labels do not overlap or resize cards unexpectedly.
- Horizontal table scrolling works on narrow viewports.

### Dataset validation

Add a generated validation summary with these gates:

- 100% of alternative records have explicit normalized transport fields.
- 100% of solution records have a classification and confidence.
- 0 cellular/eSIM records have `link_mode=wired` unless explicitly hybrid with an additional wired bearer.
- 0 `api_capable=true` records infer their link mode solely from API capability.
- 0 known media resolve to `unknown`.
- All `unknown` solution rows are listed for manual review.

### Workflow and R2 tests

- A workflow fixture that adds a new cellular/eSIM crawler record produces `link_mode=wireless` in processed CSV, frontend JSON, manifest labels, R2 snapshot content, Worker output, and UI rendering.
- A workflow fixture that adds an API-only cloud platform with no bearer evidence produces `link_mode=unknown`, never wired.
- The first and final generation passes cannot publish different catalog snapshots under the same snapshot ID.
- CI fails when frontend JSON checksums differ from the catalog checksums recorded in the R2 manifest.
- CI fails when a generated record contains an unknown bearer enum without an explicit `confidence=unknown` classification.
- R2 latest-pointer promotion is skipped when any object upload or checksum verification fails.
- The Worker rejects or reports an unhealthy catalog snapshot when the manifest and fetched catalog checksums differ.
- Both Wrangler and S3 upload paths publish the same object set and metadata.

## Acceptance Criteria

The patch is complete only when all of the following are proven:

1. `1NCE IoT eSIM` displays a wireless cellular/eSIM bearer and a separate API capability.
2. All seven known cellular/eSIM solution records avoid the wired label.
3. Legacy analog/TDM rows no longer imply API capability without explicit evidence.
4. Wired non-IP alternatives are distinguishable from physical/manual and wireless alternatives.
5. The same normalized taxonomy drives generated data, backend filtering, backend output, frontend badges, and frontend filters.
6. Missing bearer data displays as unknown/unspecified rather than wired.
7. Backend and frontend test matrices cover wired IP, wireless IP, wired non-IP, physical, manual, hybrid, and unknown cases.
8. Regenerated assets and reports contain the normalized fields.
9. Desktop and mobile UI verification confirms readable, non-overlapping badges and tables.
10. `.github/workflows/report.yml` validates the final post-notebook catalog snapshot before commit, R2 upload, and frontend build.
11. Frontend build inputs and R2 catalog objects have matching SHA-256 values recorded in the manifest.
12. New crawler context cannot be published without normalized transport fields or an explicit unknown classification.
13. R2 publication is atomic through an immutable snapshot plus latest pointer, or an equivalent verified promotion mechanism.
14. Worker responses expose the transport schema version and catalog snapshot identity used for classification.

## Recommended Implementation Order

1. Add taxonomy module and fixture tests.
2. Enrich and regenerate both catalogs.
3. Update backend response schema and exclusion handling.
4. Update frontend rendering and filters.
5. Run dataset validation and manually review unknown/hybrid classifications.
6. Run backend tests, frontend build, and browser verification.
7. Deploy backend before or together with frontend schema-v2 support.

## Key Design Decision

Do not attempt to fix this by adding `cellular` to the existing `non_network_physical` branch. Cellular is networked but wireless, and API is an interface rather than a bearer. The durable fix is to model these as separate dimensions and render them as separate badges.
