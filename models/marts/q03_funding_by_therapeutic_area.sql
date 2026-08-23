SELECT
    ds.therapeutic_area,
    ds.total_deals,
    COALESCE(fbt.total_funding_m, 0) AS total_funding_m,
    fbt.avg_funding_m,
    ds.avg_deal_value_m
FROM (
    SELECT
        ta.ta_id,
        ta.name AS therapeutic_area,
        COUNT(DISTINCT d.deal_id) AS total_deals,
        ROUND(AVG(d.total_value_m), 1) AS avg_deal_value_m
    FROM {{ ref('stg_therapeutic_areas') }} ta
    LEFT JOIN {{ ref('stg_deals') }} d ON ta.ta_id = d.ta_id
    GROUP BY ta.ta_id, ta.name
) ds
LEFT JOIN (
    SELECT
        ct.ta_id,
        ROUND(SUM(cf.total_funding_m), 1) AS total_funding_m,
        ROUND(AVG(cf.total_funding_m), 1) AS avg_funding_m
    FROM (
        SELECT DISTINCT d.ta_id, c.name AS company_name
        FROM {{ ref('stg_deals') }} d
        JOIN {{ ref('stg_companies') }} c ON d.licensor_id = c.company_id
    ) ct
    JOIN (
        SELECT cp.company_name, ROUND(SUM(fr.amount_m), 1) AS total_funding_m
        FROM {{ ref('stg_company_profiles') }} cp
        JOIN {{ ref('stg_funding_rounds') }} fr ON cp.uuid = fr.company_uuid
        GROUP BY cp.company_name
    ) cf ON ct.company_name = cf.company_name
    GROUP BY ct.ta_id
) fbt ON ds.ta_id = fbt.ta_id
ORDER BY total_funding_m DESC
