SELECT
    ci.investor_name,
    COUNT(DISTINCT ci.company_uuid) AS companies_backed,
    COUNT(DISTINCT d.deal_id) AS total_deals_by_portfolio,
    ROUND(COUNT(DISTINCT d.deal_id) / NULLIF(COUNT(DISTINCT ci.company_uuid), 0), 1) AS deals_per_company,
    ROUND(AVG(d.total_value_m), 1) AS avg_deal_value_m
FROM {{ ref('stg_investors') }} ci
JOIN {{ ref('stg_company_profiles') }} cp ON ci.company_uuid = cp.uuid
JOIN {{ ref('stg_companies') }} c ON cp.company_name = c.name
JOIN {{ ref('stg_deals') }} d ON c.company_id = d.licensor_id
WHERE ci.investor_name NOT LIKE '%fictitious%'
GROUP BY ci.investor_name
HAVING companies_backed >= 10
ORDER BY deals_per_company DESC
LIMIT 20
