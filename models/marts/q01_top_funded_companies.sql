SELECT
    f.company_name,
    f.company_type,
    f.public_private,
    f.country,
    f.primary_ta,
    f.total_funding_m,
    f.funding_rounds,
    COALESCE(dc.deal_count, 0) AS deals_as_licensor
FROM (
    SELECT
        cp.company_name,
        cp.company_type,
        cp.public_private,
        cp.country,
        cp.primary_ta,
        ROUND(SUM(fr.amount_m), 1) AS total_funding_m,
        COUNT(DISTINCT fr.funding_id) AS funding_rounds
    FROM {{ ref('stg_company_profiles') }} cp
    JOIN {{ ref('stg_funding_rounds') }} fr ON cp.uuid = fr.company_uuid
    GROUP BY cp.company_name, cp.company_type, cp.public_private, cp.country, cp.primary_ta
) f
LEFT JOIN (
    SELECT
        c.name AS company_name,
        COUNT(DISTINCT d.deal_id) AS deal_count
    FROM {{ ref('stg_companies') }} c
    JOIN {{ ref('stg_deals') }} d ON c.company_id = d.licensor_id
    GROUP BY c.name
) dc ON f.company_name = dc.company_name
ORDER BY f.total_funding_m DESC
LIMIT 20
