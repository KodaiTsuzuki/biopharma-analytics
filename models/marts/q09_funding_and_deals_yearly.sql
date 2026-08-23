WITH funding_yearly AS (
    SELECT
        funding_year AS yr,
        COUNT(*) AS funding_count,
        ROUND(SUM(amount_m), 1) AS total_funding_m
    FROM {{ ref('stg_funding_rounds') }}
    WHERE funding_year BETWEEN 2010 AND 2025
    GROUP BY funding_year
),
deals_yearly AS (
    SELECT
        deal_year AS yr,
        COUNT(DISTINCT deal_id) AS deal_count,
        ROUND(SUM(total_value_m), 1) AS total_deal_value_m
    FROM {{ ref('stg_deals') }}
    WHERE deal_year BETWEEN 2010 AND 2025
    GROUP BY deal_year
),
all_years AS (
    SELECT yr FROM funding_yearly
    UNION
    SELECT yr FROM deals_yearly
)
SELECT
    ay.yr AS year,
    f.funding_count,
    f.total_funding_m,
    d.deal_count,
    d.total_deal_value_m,
    LAG(f.funding_count) OVER (ORDER BY ay.yr) AS prev_yr_funding,
    LAG(d.deal_count) OVER (ORDER BY ay.yr) AS prev_yr_deals
FROM all_years ay
LEFT JOIN funding_yearly f ON ay.yr = f.yr
LEFT JOIN deals_yearly d ON ay.yr = d.yr
ORDER BY ay.yr
