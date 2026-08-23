SELECT
    funding_year,
    COUNT(*) AS total_rounds,
    SUM(CASE WHEN round_type = 'Venture' THEN 1 ELSE 0 END) AS venture_rounds,
    SUM(CASE WHEN round_type = 'IPO' THEN 1 ELSE 0 END) AS ipos,
    SUM(CASE WHEN round_type = 'PIPE' THEN 1 ELSE 0 END) AS pipes,
    SUM(CASE WHEN round_type = 'Grant' THEN 1 ELSE 0 END) AS grants,
    ROUND(SUM(CASE WHEN round_type = 'IPO' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) AS ipo_pct
FROM {{ ref('stg_funding_rounds') }}
WHERE funding_year BETWEEN 2010 AND 2025
GROUP BY funding_year
ORDER BY funding_year
