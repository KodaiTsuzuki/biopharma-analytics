SELECT 
  funding_id,
  company_uuid,
  company_name,
  funding_title,
  amount_m,
  round_type,
  announced_date,
  funding_year,
  funding_status,
  stage_at_funding,
  primary_ta,
  lead_investor,
  country
FROM {{ source('dealforma', 'funding_rounds') }}
