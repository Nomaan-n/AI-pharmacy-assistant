# Indian medicine catalog sync: 2026-08-28

## Primary catalog source

- Indian Medicine Dataset: `junioralive/Indian-Medicine-Dataset`
- Latest public repository update observed: 2026-06-27
- Dataset size documented upstream: 253,973 medicine records
- Active filtering rule: exclude records whose `Is_discontinued` is TRUE/1/YES/Y
- Upstream license: MIT
- Source: https://github.com/junioralive/Indian-Medicine-Dataset

The build continues to fetch the upstream CSV at build time and keeps only records not explicitly marked discontinued. The repository does not claim that absence of a discontinued flag is equivalent to CDSCO marketing authorization.

## Verified additions

Six currently listed Indian branded products were added as a supplemental layer because they are newer than the June 2026 upstream snapshot and have independent current product evidence:

- Brexilo 0.25 Tablet: brexpiprazole 0.25 mg, Torrent Pharmaceuticals Ltd
- Brexilo 0.5 Tablet: brexpiprazole 0.5 mg, Torrent Pharmaceuticals Ltd
- Brexilo 1 Tablet: brexpiprazole 1 mg, Torrent Pharmaceuticals Ltd
- Brexilo 2 Tablet: brexpiprazole 2 mg, Torrent Pharmaceuticals Ltd
- Brexilo 3 Tablet: brexpiprazole 3 mg, Torrent Pharmaceuticals Ltd
- Brexilo 4 Tablet: brexpiprazole 4 mg, Torrent Pharmaceuticals Ltd

Current 1mg listings show these products as orderable Indian products and identify Torrent Pharmaceuticals Ltd as marketer. The pages were updated 2026-08-25/27.

CDSCO's official searchable drug database shows brexpiprazole finished-formulation approvals on 2026-07-01 and 2026-08-03, including 0.25/0.5/1/2/3/4 mg tablet strengths.

## Deliberately not added

- Sotorasib/Lumakras: CDSCO approval evidence exists, but current Indian market evidence located in this sync describes it as not commercially marketed in India and available via named-patient import. It is therefore not added to the active Indian marketed catalog.
- Other August 2026 CDSCO FDC/SND/BIO approvals: approval alone was not treated as proof that a specific Indian marketed brand is currently active. Where no independent current product listing could be verified, the record was left out rather than inferred.

## Verification limitations

1. CDSCO approval is regulatory evidence, not a guarantee that a product is currently marketed or stocked.
2. The public Indian Medicine Dataset is large and has an explicit discontinuation field, but its latest observed repository update predates this sync by about two months.
3. Current Indian commercial availability was checked using current product listings for the six Brexilo additions. This is not a substitute for a manufacturer-held master product registry.
4. No proprietary commercial Indian medicine database was used.
5. No medicine identity was inferred from a generic name alone when a current brand/product identity could not be independently verified.

## Build behavior

`scripts/build_india_index.py` now merges the upstream active-only dataset with `data/verified_india_additions.csv`, deduplicating supplemental rows against the upstream normalized name, manufacturer and composition.
