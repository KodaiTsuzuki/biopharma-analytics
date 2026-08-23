WITH first_funding AS (
    SELECT
        company_uuid,
        company_name,
        MIN(announced_date) AS first_funding_date
    FROM {{ ref('stg_funding_rounds') }}
    GROUP BY company_uuid, company_name
),
first_deal AS (
    SELECT
        c.name AS company_name,
        MIN(d.announced_date) AS first_deal_date
    FROM {{ ref('stg_deals') }} d
    JOIN {{ ref('stg_companies') }} c ON d.licensor_id = c.company_id
    GROUP BY c.name
),
journey AS (
    SELECT
        ff.company_name,
        cp.latest_stage,
        ROUND(DATEDIFF(fd.first_deal_date, ff.first_funding_date) / 365.25, 1) AS years_to_first_deal
    FROM first_funding ff
    JOIN {{ ref('stg_company_profiles') }} cp ON ff.company_uuid = cp.uuid
    JOIN first_deal fd ON ff.company_name = fd.company_name
    WHERE ff.first_funding_date IS NOT NULL
      AND fd.first_deal_date IS NOT NULL
      AND fd.first_deal_date > ff.first_funding_date
)
SELECT
    latest_stage,
    COUNT(*) AS companies,
    ROUND(AVG(years_to_first_deal), 1) AS avg_years_to_deal,
    ROUND(MIN(years_to_first_deal), 1) AS fastest_years,
    ROUND(MAX(years_to_first_deal), 1) AS slowest_years
FROM journey
WHERE latest_stage NOT IN ('Not Applicable', 'Not Disclosed')
GROUP BY latest_stage
HAVING companies >= 5
ORDER BY avg_years_to_deal
