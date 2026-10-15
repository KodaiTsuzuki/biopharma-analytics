# Biopharma Deal Intelligence (dbt)

A dbt project that turns a DealForma biopharma dataset (~51,000 records across 8 MySQL tables) into 6 staging models and 10 analytical models. Dashboards were built in Tableau.

## Stack
MySQL, dbt Core (dbt-mysql adapter), Python (pandas) for cross-checking, Tableau, Git/GitHub.

## Structure
- `models/staging/`: 6 models (companies, company_profiles, deals, funding_rounds, investors, therapeutic_areas) that select the needed columns from the raw tables.
- `models/marts/`: 10 models (q01 to q10), one per analysis, built on the staging models with `ref()`.
- `biopharma_analysis.py`: the Python script used to independently reproduce the SQL analyses.

All models are materialized as views in a local MySQL database. The raw data is proprietary and is not included in this repo.

## Data quality checks
- 14 dbt tests on the staging layer: unique and not_null on key IDs, plus relationship tests (deals to companies, funding rounds to company profiles). Run with `dbt test`.
- An independent Python implementation of the analyses, used to cross-check the SQL results.
- Found during testing: the dataset has no `Venture` or `Grant` round types, so Q05 reports `ipos`, `pipes` and `other_rounds` (which sum to the total each year).

## Known limitations
- Several models join `company_profiles` to `companies` by company name. About 40% of profiles have no exact name match, which is expected where a company has no deals. A cleaner match recovered only 19 more profiles, but that check only covers two naming patterns, so the real figure could be somewhat higher.
- Tests cover staging keys and two relationships. They do not validate the analytical models.
- 2025 data may be understated because of reporting lag in the source.
