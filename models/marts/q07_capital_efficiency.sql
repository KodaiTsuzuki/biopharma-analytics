SELECT
    f.company_name,
    f.company_type,
    f.primary_ta,
    f.total_funding_m,
    dv.total_deal_value_m,
    dv.deal_count,
    ROUND(dv.total_deal_value_m / NULLIF(f.total_funding_m, 0), 1) AS deal_to_funding_ratio
FROM (
    SELECT
        cp.company_name,
        cp.company_type,
        cp.primary_ta,
        ROUND(SUM(fr.amount_m), 1) AS total_funding_m
    FROM {{ ref('stg_company_profiles') }} cp
    JOIN {{ ref('stg_funding_rounds') }} fr ON cp.uuid = fr.company_uuid
    GROUP BY cp.company_name, cp.company_type, cp.primary_ta
) f
JOIN (
    SELECT
        c.name AS company_name,
        ROUND(SUM(d.total_value_m), 1) AS total_deal_value_m,
        COUNT(DISTINCT d.deal_id) AS deal_count
    FROM {{ ref('stg_companies') }} c
    JOIN {{ ref('stg_deals') }} d ON c.company_id = d.licensor_id
    GROUP BY c.name
) dv ON f.company_name = dv.company_name
WHERE f.total_funding_m > 0 AND dv.total_deal_value_m > 0
ORDER BY deal_to_funding_ratio DESC
LIMIT 20
