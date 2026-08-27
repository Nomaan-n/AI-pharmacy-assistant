# AI Pharmacy Assistant

Safety-aware medicine intelligence for Indian medicine names, brands and generics.

## Medicine catalog

The production build imports the public **Indian Medicine Dataset**, which contains 253,973 medicine records and an explicit `Is_discontinued` field. The build keeps records not marked discontinued and creates a local SQLite index for fast offline-first lookup. This means brand-name queries do not depend on a tiny hand-maintained list. The upstream dataset is MIT licensed and documents fields for product name, manufacturer, composition, price, pack size and discontinuation status. citeturn1search0

The runtime resolver supports:
- exact brand-name lookup
- normalized spelling, spaces and hyphens
- prefix and substring lookup
- composition/generic lookup
- RxNorm/NLM fallback
- openFDA fallback
- DailyMed evidence retrieval
- curated high-confidence Indian brand overrides

CDSCO remains the authoritative regulatory reference for Indian new-drug approvals and marketing information; the catalog is treated as an availability/search index, not as regulatory approval evidence. citeturn0search0turn0search1

## Deployment

Render builds the medicine index from the upstream CSV on every deployment. No Google Cloud billing or Programmable Search Engine is required.
