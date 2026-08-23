SELECT
    ci.investor_name,
    COUNT(DISTINCT ci.company_uuid) AS companies_backed,
    COUNT(DISTINCT cp.primary_ta) AS ta_diversity,
    GROUP_CONCAT(DISTINCT cp.primary_ta ORDER BY cp.primary_ta SEPARATOR ', ') AS therapeutic_areas
FROM {{ ref('stg_investors') }} ci
JOIN {{ ref('stg_company_profiles') }} cp ON ci.company_uuid = cp.uuid
WHERE ci.investor_name NOT LIKE '%fictitious%'
GROUP BY ci.investor_name
HAVING companies_backed >= 50
ORDER BY companies_backed DESC
LIMIT 20
