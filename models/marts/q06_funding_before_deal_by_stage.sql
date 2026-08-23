WITH first_deal AS (
    SELECT
        c.company_id,
        c.name AS company_name,
        MIN(d.announced_date) AS first_deal_date
    FROM {{ ref('stg_deals') }} d
    JOIN {{ ref('stg_companies') }} c ON d.licensor_id = c.company_id
    GROUP BY c.company_id, c.name
),
funding_before_deal AS (
    SELECT
        fd.company_name,
        cp.latest_stage,
        SUM(fr.amount_m) AS total_funding_before_deal
    FROM first_deal fd
    JOIN {{ ref('stg_company_profiles') }} cp ON fd.company_name = cp.company_name
    JOIN {{ ref('stg_funding_rounds') }} fr ON cp.uuid = fr.company_uuid
    WHERE fr.announced_date < fd.first_deal_date
    GROUP BY fd.company_name, cp.latest_stage
)
SELECT
    latest_stage,
    COUNT(*) AS companies,
    ROUND(AVG(total_funding_before_deal), 1) AS avg_funding_before_deal_m,
    ROUND(MIN(total_funding_before_deal), 1) AS min_funding_m,
    ROUND(MAX(total_funding_before_deal), 1) AS max_funding_m
FROM funding_before_deal
WHERE latest_stage NOT IN ('Not Applicable', 'Not Disclosed')
GROUP BY latest_stage
HAVING companies >= 5
ORDER BY avg_funding_before_deal_m
