SELECT
    cp.public_private,
    COUNT(DISTINCT d.deal_id) AS total_deals,
    COUNT(DISTINCT cp.uuid) AS unique_companies,
    ROUND(SUM(d.total_value_m), 1) AS total_deal_value_m,
    ROUND(AVG(d.total_value_m), 1) AS avg_deal_value_m
FROM {{ ref('stg_company_profiles') }} cp
JOIN {{ ref('stg_companies') }} c ON cp.company_name = c.name
JOIN {{ ref('stg_deals') }} d ON c.company_id = d.licensor_id
GROUP BY cp.public_private
ORDER BY total_deal_value_m DESC
