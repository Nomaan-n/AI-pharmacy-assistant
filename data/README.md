# Active Indian medicine catalog

The catalog is intended to contain currently listed Indian medicines only.

## Inclusion rule

Only records with `Is_discontinued = FALSE` in the upstream Indian medicine dataset are imported. Discontinued records are excluded from the generated catalog.

## Source

The current upstream source is the Indian Medicine Dataset:
https://github.com/junioralive/Indian-Medicine-Dataset

For regulatory/new-drug changes, prefer official CDSCO publications and approval notices over third-party datasets.

## Update policy

The catalog should be refreshed daily. A refresh must preserve the discontinued filter and should not silently turn an unverified product into a verified medicine identity.
