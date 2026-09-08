# =============================================================
# Biopharma Deal Intelligence Project
# Author: Kodai Tsuzuki
# Organization: Crossover Search Partners
# Description: Independent pandas reimplementation of the 10
#              analyses in queries.sql. This file contains ZERO
#              SQL beyond simple, single-table SELECTs - every
#              join, GROUP BY, ranking, and date calculation is
#              done in pandas instead. The point is validation:
#              two independently-written implementations (SQL vs.
#              pandas) should land on the same numbers. Where they
#              don't, that's a signal one of them has a bug - see
#              the VALIDATION NOTE blocks on Q01, Q03, and Q07.
# Data Source: DealForma (~51,000 records across 8 tables)
# =============================================================

import mysql.connector
import pandas as pd
from sqlalchemy import create_engine

# Connect to MySQL via SQLAlchemy
import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from a local .env file

db_user = os.getenv("MYSQL_USER")
db_password = os.getenv("MYSQL_PASSWORD")
db_host = os.getenv("MYSQL_HOST", "localhost")
db_name = os.getenv("MYSQL_DB", "biopharma")

engine = create_engine(
    f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}"
)

print("Connection successful!")
print("=" * 60)

# =============================================================
# Raw table pulls - simple SELECTs only, no joins, no GROUP BY,
# no window functions. Everything relational happens in pandas
# below, on these six tables.
# =============================================================
raw_company_profiles = pd.read_sql(
    "SELECT uuid, company_name, company_type, public_private, country, primary_ta, "
    "latest_stage FROM company_profiles",
    engine,
)
raw_funding_rounds = pd.read_sql(
    "SELECT funding_id, company_uuid, company_name AS fr_company_name, amount_m, "
    "funding_year, round_type, announced_date FROM funding_rounds",
    engine,
)
raw_companies = pd.read_sql(
    "SELECT company_id, name AS co_name FROM companies", engine
)
raw_deals = pd.read_sql(
    "SELECT deal_id, licensor_id, announced_date, total_value_m, ta_id, deal_year FROM deals",
    engine,
)
raw_company_investors = pd.read_sql(
    "SELECT investor_name, company_uuid FROM company_investors", engine
)
raw_therapeutic_areas = pd.read_sql(
    "SELECT ta_id, name AS therapeutic_area FROM therapeutic_areas", engine
)

# Some MySQL drivers hand back DATE columns as plain python date objects
# instead of pandas datetime64 - force the conversion so date comparisons
# and .dt accessors below behave consistently regardless of driver.
raw_funding_rounds["announced_date"] = pd.to_datetime(raw_funding_rounds["announced_date"])
raw_deals["announced_date"] = pd.to_datetime(raw_deals["announced_date"])

for _name, _df in [
    ("company_profiles", raw_company_profiles),
    ("funding_rounds", raw_funding_rounds),
    ("companies", raw_companies),
    ("deals", raw_deals),
    ("company_investors", raw_company_investors),
    ("therapeutic_areas", raw_therapeutic_areas),
]:
    print(f"  Pulled {_name}: {len(_df)} rows")

# =============================================================
# Q01 - Top funded companies vs deal activity
# =============================================================
# VALIDATION NOTE: the original queries.sql joined funding_rounds and
# deals off the same company in a single query, which fans out - a
# company with 2 funding rounds and 3 deals produced 6 joined rows, so
# SUM(fr.amount_m) counted each round up to 3x. Fixed here (and in
# queries.sql) by totaling funding and totaling deals in two separate
# aggregations first, then combining - so a company's totals aren't
# inflated by how many rows sit on the other side of the join.
#
# Field list (company_type, public_private, country, funding_rounds,
# deals_as_licensor) matches the Tableau worksheet this feeds
# (top_funded_companies, inside the d4_capital_efficiency dashboard).
funding_by_company = (
    raw_company_profiles.merge(raw_funding_rounds, left_on="uuid", right_on="company_uuid")
    .groupby(["company_name", "company_type", "public_private", "country", "primary_ta"])
    .agg(total_funding_m=("amount_m", "sum"), funding_rounds=("funding_id", "nunique"))
    .round(1)
    .reset_index()
)
deals_by_company = (
    raw_companies.merge(raw_deals, left_on="company_id", right_on="licensor_id")
    .groupby("co_name")["deal_id"]
    .nunique()
    .reset_index(name="deals_as_licensor")
)
df_q01 = funding_by_company.merge(
    deals_by_company, left_on="company_name", right_on="co_name", how="left"
)
df_q01["deals_as_licensor"] = df_q01["deals_as_licensor"].fillna(0).astype(int)
df_q01 = df_q01[
    ["company_name", "company_type", "public_private", "country", "primary_ta",
     "total_funding_m", "funding_rounds", "deals_as_licensor"]
]
df_q01 = df_q01.sort_values("total_funding_m", ascending=False).head(20).reset_index(drop=True)

# Rank companies by total funding (pandas-side ranking)
df_q01["funding_rank"] = df_q01["total_funding_m"].rank(ascending=False, method="min").astype(int)

print("\nQ01 - Top Funded Companies vs Deal Activity")
print("-" * 60)
print(df_q01)
df_q01.to_csv("q01_top_funded_companies.csv", index=False)
print("Exported: q01_top_funded_companies.csv")

# =============================================================
# Q02 - Deals by public/private/subsidiary status
# =============================================================
# Groups by public_private (not company_type) and counts unique
# companies via company_profiles' uuid, matching the actual Tableau
# worksheet (deal_value_by_type, inside d5_deal_ready_profile).
q02_base = (
    raw_company_profiles.merge(raw_companies, left_on="company_name", right_on="co_name")
    .merge(raw_deals, left_on="company_id", right_on="licensor_id")
)
df_q02 = (
    q02_base.groupby("public_private")
    .agg(
        total_deals=("deal_id", "nunique"),
        unique_companies=("uuid", "nunique"),
        total_deal_value_m=("total_value_m", "sum"),
        avg_deal_value_m=("total_value_m", "mean"),
    )
    .round(1)
    .reset_index()
)
df_q02 = df_q02.sort_values("total_deal_value_m", ascending=False).reset_index(drop=True)

print("\nQ02 - Deals by Company Type (Public/Private/Subsidiary/N/A)")
print("-" * 60)
print(df_q02)
df_q02.to_csv("q02_deals_by_company_type.csv", index=False)
print("Exported: q02_deals_by_company_type.csv")

# =============================================================
# Q03 - Funding vs deals by therapeutic area
# =============================================================
# VALIDATION NOTE: same fan-out family as Q01. The original SQL chained
# therapeutic_areas -> deals -> companies -> company_profiles ->
# funding_rounds in one query, so a company with multiple deals in a TA
# had its funding summed once per deal. Fixed here (and in queries.sql)
# by first building the distinct set of (company, TA) pairs implied by
# deals, then joining each company's already-totaled funding onto that
# - so funding is added once per company-TA pair, not once per deal.
company_ta = (
    raw_deals.merge(raw_companies, left_on="licensor_id", right_on="company_id")[
        ["ta_id", "co_name"]
    ]
    .drop_duplicates()
)
company_funding = (
    raw_company_profiles.merge(raw_funding_rounds, left_on="uuid", right_on="company_uuid")
    .groupby("company_name")["amount_m"]
    .sum()
    .round(1)
    .reset_index(name="total_funding_m")
)
funding_by_ta = (
    company_ta.merge(company_funding, left_on="co_name", right_on="company_name")
    .groupby("ta_id")
    .agg(total_funding_m=("total_funding_m", "sum"), avg_funding_m=("total_funding_m", "mean"))
    .round(1)
    .reset_index()
)
deal_stats = (
    raw_therapeutic_areas.merge(raw_deals, on="ta_id", how="left")
    .groupby(["ta_id", "therapeutic_area"])
    .agg(total_deals=("deal_id", "nunique"), avg_deal_value_m=("total_value_m", "mean"))
    .round(1)
    .reset_index()
)
df_q03 = deal_stats.merge(funding_by_ta, on="ta_id", how="left")
df_q03["total_funding_m"] = df_q03["total_funding_m"].fillna(0)
df_q03 = df_q03[
    ["therapeutic_area", "total_deals", "total_funding_m", "avg_funding_m", "avg_deal_value_m"]
]
df_q03 = df_q03.sort_values("total_funding_m", ascending=False).reset_index(drop=True)

print("\nQ03 - Funding vs Deals by Therapeutic Area")
print("-" * 60)
print(df_q03)
df_q03.to_csv("q03_funding_by_therapeutic_area.csv", index=False)
print("Exported: q03_funding_by_therapeutic_area.csv")

# =============================================================
# Q04 - Top investors by portfolio size and therapeutic-area diversity
# =============================================================
inv04 = raw_company_investors[
    ~raw_company_investors["investor_name"].str.contains("fictitious", case=False, na=False)
]
inv04 = inv04.merge(raw_company_profiles, left_on="company_uuid", right_on="uuid")

df_q04 = (
    inv04.groupby("investor_name")
    .agg(
        companies_backed=("company_uuid", "nunique"),
        ta_diversity=("primary_ta", "nunique"),
        therapeutic_areas=("primary_ta", lambda s: ", ".join(sorted(s.dropna().unique()))),
    )
    .reset_index()
)
df_q04 = df_q04[df_q04["companies_backed"] >= 50]
df_q04 = df_q04.sort_values("companies_backed", ascending=False).head(20).reset_index(drop=True)

print("\nQ04 - Top Investors by Portfolio Size and TA Diversity")
print("-" * 60)
print(df_q04)
df_q04.to_csv("q04_top_investors.csv", index=False)
print("Exported: q04_top_investors.csv")

# =============================================================
# Q05 - Funding timeline by round type, with IPO share of rounds
# =============================================================
fr05 = raw_funding_rounds[
    (raw_funding_rounds["funding_year"] >= 2010) & (raw_funding_rounds["funding_year"] <= 2025)
]
counts05 = fr05.groupby("funding_year").size().reset_index(name="total_rounds")
pivot05 = fr05.pivot_table(
    index="funding_year", columns="round_type", values="amount_m", aggfunc="count", fill_value=0
).reset_index()
for _col in ["Venture", "IPO", "PIPE", "Grant"]:
    if _col not in pivot05.columns:
        pivot05[_col] = 0

df_q05 = counts05.merge(pivot05[["funding_year", "Venture", "IPO", "PIPE", "Grant"]], on="funding_year")
df_q05 = df_q05.rename(columns={"Venture": "venture", "IPO": "ipo", "PIPE": "pipe", "Grant": "grant"})
df_q05["ipo_pct"] = (df_q05["ipo"] / df_q05["total_rounds"] * 100).round(1)
df_q05 = df_q05.sort_values("funding_year").reset_index(drop=True)

# 3-year rolling average of total funding rounds, smooths year-to-year noise
df_q05["rounds_3yr_rolling_avg"] = (
    df_q05["total_rounds"].rolling(window=3, min_periods=1).mean().round(1)
)

print("\nQ05 - Funding Timeline by Type")
print("-" * 60)
print(df_q05)
df_q05.to_csv("q05_funding_timeline.csv", index=False)
print("Exported: q05_funding_timeline.csv")

# =============================================================
# Q06 - Average funding raised before a company's first deal,
#        by clinical stage
# =============================================================
first_deal06 = (
    raw_companies.merge(raw_deals, left_on="company_id", right_on="licensor_id")
    .groupby("co_name")["announced_date"]
    .min()
    .reset_index(name="first_deal_date")
)
funding_before_deal = first_deal06.merge(
    raw_company_profiles, left_on="co_name", right_on="company_name"
).merge(raw_funding_rounds, left_on="uuid", right_on="company_uuid")
funding_before_deal = funding_before_deal[
    funding_before_deal["announced_date"] < funding_before_deal["first_deal_date"]
]
per_company06 = (
    funding_before_deal.groupby(["company_name", "latest_stage"])["amount_m"]
    .sum()
    .reset_index(name="total_funding_before_deal")
)
df_q06 = (
    per_company06[~per_company06["latest_stage"].isin(["Not Applicable", "Not Disclosed"])]
    .groupby("latest_stage")
    .agg(
        companies=("company_name", "count"),
        avg_funding_before_deal_m=("total_funding_before_deal", "mean"),
        min_funding_m=("total_funding_before_deal", "min"),
        max_funding_m=("total_funding_before_deal", "max"),
    )
    .round(1)
    .reset_index()
)
df_q06 = df_q06[df_q06["companies"] >= 5].sort_values("avg_funding_before_deal_m").reset_index(drop=True)

print("\nQ06 - Average Funding Before First Deal by Clinical Stage")
print("-" * 60)
print(df_q06)
df_q06.to_csv("q06_funding_before_deal.csv", index=False)
print("Exported: q06_funding_before_deal.csv")

# =============================================================
# Q07 - Capital efficiency: deal value generated per funding
#        dollar raised
# =============================================================
# VALIDATION NOTE: same fan-out bug as Q01, and it distorted this query
# worse because BOTH sides of the ratio were inflated by different
# amounts. The original SQL joined funding_rounds and deals off the same
# company in one query, so SUM(fr.amount_m) got multiplied by that
# company's deal count and SUM(d.total_value_m) got multiplied by that
# company's funding-round count - two different multipliers on
# numerator and denominator, which can flip rankings, not just rescale
# them. Fixed here (and in queries.sql) by totaling funding and deal
# value in two separate aggregations before computing the ratio.
funding07 = (
    raw_company_profiles.merge(raw_funding_rounds, left_on="uuid", right_on="company_uuid")
    .groupby(["company_name", "company_type", "primary_ta"])["amount_m"]
    .sum()
    .round(1)
    .reset_index(name="total_funding_m")
)
deals_val07 = (
    raw_companies.merge(raw_deals, left_on="company_id", right_on="licensor_id")
    .groupby("co_name")
    .agg(total_deal_value_m=("total_value_m", "sum"), deal_count=("deal_id", "nunique"))
    .reset_index()
)
deals_val07["total_deal_value_m"] = deals_val07["total_deal_value_m"].round(1)
df_q07 = funding07.merge(deals_val07, left_on="company_name", right_on="co_name", how="inner")
df_q07 = df_q07[(df_q07["total_funding_m"] > 0) & (df_q07["total_deal_value_m"] > 0)]
df_q07["deal_to_funding_ratio"] = (df_q07["total_deal_value_m"] / df_q07["total_funding_m"]).round(1)
df_q07 = df_q07[
    ["company_name", "company_type", "primary_ta", "total_funding_m",
     "total_deal_value_m", "deal_count", "deal_to_funding_ratio"]
]
df_q07 = df_q07.sort_values("deal_to_funding_ratio", ascending=False).head(20).reset_index(drop=True)

print("\nQ07 - Capital Efficiency and M&A Hall of Fame")
print("-" * 60)
print(df_q07)
df_q07.to_csv("q07_capital_efficiency.csv", index=False)
print("Exported: q07_capital_efficiency.csv")

# =============================================================
# Q08 - Investor deal velocity (deals per portfolio company)
# =============================================================
inv08 = raw_company_investors[
    ~raw_company_investors["investor_name"].str.contains("fictitious", case=False, na=False)
]
inv_deals08 = (
    inv08.merge(raw_company_profiles, left_on="company_uuid", right_on="uuid")
    .merge(raw_companies, left_on="company_name", right_on="co_name")
    .merge(raw_deals, left_on="company_id", right_on="licensor_id")
)
df_q08 = (
    inv_deals08.groupby("investor_name")
    .agg(
        companies_backed=("company_uuid", "nunique"),
        total_deals_by_portfolio=("deal_id", "nunique"),
        avg_deal_value_m=("total_value_m", "mean"),
    )
    .reset_index()
)
df_q08 = df_q08[df_q08["companies_backed"] >= 10]
df_q08["deals_per_company"] = (
    df_q08["total_deals_by_portfolio"] / df_q08["companies_backed"]
).round(1)
df_q08["avg_deal_value_m"] = df_q08["avg_deal_value_m"].round(1)
df_q08 = df_q08.sort_values("deals_per_company", ascending=False).head(20).reset_index(drop=True)
df_q08 = df_q08[
    ["investor_name", "companies_backed", "total_deals_by_portfolio", "deals_per_company", "avg_deal_value_m"]
]

print("\nQ08 - Investor Deal Velocity")
print("-" * 60)
print(df_q08)
df_q08.to_csv("q08_investor_deal_velocity.csv", index=False)
print("Exported: q08_investor_deal_velocity.csv")

# =============================================================
# Q09 - Year-over-year funding rounds vs deal activity
# =============================================================
# The Tableau worksheet this feeds (funding_vs_deals_trend, inside
# d1_market_cycles) tracks funding rounds AND deal activity together by
# year. funding_rounds and deals are aggregated independently by year
# first (fan-out-safe - no direct row-level join between them), then
# combined on year via an outer-join-style merge (pandas merge(how="outer")
# is the equivalent of the UNION-of-years + LEFT JOINs used in queries.sql,
# since MySQL has no FULL OUTER JOIN).
fr09 = raw_funding_rounds[
    (raw_funding_rounds["funding_year"] >= 2010) & (raw_funding_rounds["funding_year"] <= 2025)
]
funding_yearly = (
    fr09.groupby("funding_year")
    .agg(funding_count=("amount_m", "count"), total_funding_m=("amount_m", "sum"))
    .round(1)
    .reset_index()
    .rename(columns={"funding_year": "year"})
)
deals09 = raw_deals[(raw_deals["deal_year"] >= 2010) & (raw_deals["deal_year"] <= 2025)]
deals_yearly = (
    deals09.groupby("deal_year")
    .agg(deal_count=("deal_id", "nunique"), total_deal_value_m=("total_value_m", "sum"))
    .round(1)
    .reset_index()
    .rename(columns={"deal_year": "year"})
)
df_q09 = funding_yearly.merge(deals_yearly, on="year", how="outer").sort_values("year").reset_index(drop=True)

df_q09["prev_yr_funding"] = df_q09["funding_count"].shift(1)
df_q09["prev_yr_deals"] = df_q09["deal_count"].shift(1)
df_q09["funding_count_yoy_pct"] = (
    (df_q09["funding_count"] - df_q09["prev_yr_funding"]) / df_q09["prev_yr_funding"] * 100
).round(1)
df_q09["deal_count_yoy_pct"] = (
    (df_q09["deal_count"] - df_q09["prev_yr_deals"]) / df_q09["prev_yr_deals"] * 100
).round(1)

# Funding-dollar YoY % change via pandas. The SQL only computes YoY for
# funding *count* and deal *count* (via LAG); it never touches YoY for
# funding *dollars*. That gap is filled here with pct_change() rather than
# adding a third window function to the SQL.
df_q09["funding_dollars_yoy_pct"] = (df_q09["total_funding_m"].pct_change() * 100).round(1)

print("\nQ09 - Year-over-Year Funding Rounds and Deals")
print("-" * 60)
print(df_q09)
df_q09.to_csv("q09_yoy_funding.csv", index=False)
print("Exported: q09_yoy_funding.csv")

# =============================================================
# Q10 - Time from first funding to first deal, by clinical stage
# =============================================================
first_funding10 = (
    raw_funding_rounds.groupby(["company_uuid", "fr_company_name"])["announced_date"]
    .min()
    .reset_index(name="first_funding_date")
    .rename(columns={"fr_company_name": "company_name"})
)
first_deal10 = (
    raw_companies.merge(raw_deals, left_on="company_id", right_on="licensor_id")
    .groupby("co_name")["announced_date"]
    .min()
    .reset_index(name="first_deal_date")
)
journey = first_funding10.merge(
    raw_company_profiles, left_on="company_uuid", right_on="uuid", suffixes=("", "_cp")
)
journey = journey.merge(first_deal10, left_on="company_name", right_on="co_name")
journey = journey[
    journey["first_funding_date"].notna()
    & journey["first_deal_date"].notna()
    & (journey["first_deal_date"] > journey["first_funding_date"])
]
journey["years_to_first_deal"] = (
    (journey["first_deal_date"] - journey["first_funding_date"]).dt.days / 365.25
).round(1)

df_q10 = (
    journey[~journey["latest_stage"].isin(["Not Applicable", "Not Disclosed"])]
    .groupby("latest_stage")
    .agg(
        companies=("company_name", "count"),
        avg_years_to_deal=("years_to_first_deal", "mean"),
        fastest_years=("years_to_first_deal", "min"),
        slowest_years=("years_to_first_deal", "max"),
    )
    .round(1)
    .reset_index()
)
df_q10 = df_q10[df_q10["companies"] >= 5].sort_values("avg_years_to_deal").reset_index(drop=True)

# Rank clinical stages by speed to first deal (fastest = rank 1)
df_q10["speed_rank"] = df_q10["avg_years_to_deal"].rank(method="min").astype(int)

print("\nQ10 - Time to First Deal by Clinical Stage")
print("-" * 60)
print(df_q10)
df_q10.to_csv("q10_time_to_first_deal.csv", index=False)
print("Exported: q10_time_to_first_deal.csv")

# =============================================================
# Q11 - Combined investor profile (cross-query pandas merge)
# =============================================================
# Joins Q04's portfolio/TA-diversity view with Q08's deal-velocity view on
# investor_name - a pandas-side join across two already-aggregated
# results, the kind of step that's often easier in pandas than folding
# everything into one wider query.
df_q11 = df_q04.merge(
    df_q08[["investor_name", "total_deals_by_portfolio", "deals_per_company", "avg_deal_value_m"]],
    on="investor_name",
    how="inner",
)
print("\nQ11 - Combined Investor Profile (Q04 x Q08 merge)")
print("-" * 60)
print(df_q11)
df_q11.to_csv("q11_investor_profile_combined.csv", index=False)
print("Exported: q11_investor_profile_combined.csv")

# =============================================================
# BONUS - Pure-pandas cross-tab: Therapeutic Area x Company Type
# =============================================================
# Answers a question none of Q01-Q10 answer on their own: how funding
# and deal value break down by therapeutic area *and* company type
# simultaneously. Reuses the raw pulls from the top of the file.
#
# Note: funding and deals are pre-aggregated per company BEFORE being
# combined - the same fan-out fix applied to Q01/Q03/Q07 above, and
# necessary for the same reason: a company can have several funding
# rounds and several deals, so joining those two 1:N tables together
# directly (before aggregating either one) would multiply, not add.
company_funding_bonus = (
    raw_company_profiles.merge(raw_funding_rounds, left_on="uuid", right_on="company_uuid")
    .groupby(["company_name", "company_type", "primary_ta"])
    .agg(total_funding_m=("amount_m", "sum"), funding_rounds=("amount_m", "count"))
    .reset_index()
)
company_deals_bonus = (
    raw_companies.merge(raw_deals, left_on="company_id", right_on="licensor_id")
    .groupby("co_name")
    .agg(total_deal_value_m=("total_value_m", "sum"), deal_count=("deal_id", "nunique"))
    .reset_index()
)
combined = company_funding_bonus.merge(
    company_deals_bonus, left_on="company_name", right_on="co_name", how="left"
)
combined["total_deal_value_m"] = combined["total_deal_value_m"].fillna(0)
combined["deal_count"] = combined["deal_count"].fillna(0).astype(int)

# pandas groupby: two-key aggregation (therapeutic area x company type)
ta_type_summary = (
    combined.groupby(["primary_ta", "company_type"])
    .agg(
        total_funding_m=("total_funding_m", "sum"),
        funding_rounds=("funding_rounds", "sum"),
        total_deal_value_m=("total_deal_value_m", "sum"),
        deal_count=("deal_count", "sum"),
    )
    .reset_index()
)
ta_type_summary["deal_to_funding_ratio"] = (
    ta_type_summary["total_deal_value_m"] / ta_type_summary["total_funding_m"]
).round(1)

print("\nBONUS - Funding & Deal Value by Therapeutic Area x Company Type")
print("-" * 60)
print(ta_type_summary)
ta_type_summary.to_csv("bonus_ta_by_company_type.csv", index=False)
print("Exported: bonus_ta_by_company_type.csv")

# pandas pivot_table: reshape into a TA x company-type funding matrix
funding_pivot = pd.pivot_table(
    ta_type_summary,
    index="primary_ta",
    columns="company_type",
    values="total_funding_m",
    aggfunc="sum",
    fill_value=0,
)
print("\nBONUS - Funding Matrix: Therapeutic Area x Company Type ($M)")
print("-" * 60)
print(funding_pivot)
funding_pivot.to_csv("bonus_funding_pivot.csv")
print("Exported: bonus_funding_pivot.csv")


# pandas apply(): row-wise custom capital-efficiency tier. Row-wise (not a
# single-column .apply()) because "no deals yet" needs to be distinguished
# from "a real ratio of 0" - deal_count is 0 in the first case but sum()
# silently treats a missing deal value as 0, so the ratio alone can't tell
# the two apart.
def efficiency_tier(row):
    if row["deal_count"] == 0:
        return "No deals"
    elif row["deal_to_funding_ratio"] < 5:
        return "Low"
    elif row["deal_to_funding_ratio"] < 20:
        return "Medium"
    else:
        return "High"


ta_type_summary["efficiency_tier"] = ta_type_summary.apply(efficiency_tier, axis=1)
print("\nBONUS - Capital Efficiency Tiers by Therapeutic Area x Company Type")
print("-" * 60)
print(ta_type_summary[["primary_ta", "company_type", "deal_to_funding_ratio", "efficiency_tier"]])
ta_type_summary.to_csv("bonus_efficiency_tiers.csv", index=False)
print("Exported: bonus_efficiency_tiers.csv")

print("\n" + "=" * 60)
print("Done. 14 CSVs exported - all analysis above is pure pandas,")
print("independently reimplemented from raw table pulls (no SQL logic")
print("beyond the plain SELECTs at the top of this file).")
