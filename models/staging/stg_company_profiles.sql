SELECT 
  uuid,
  company_name,
  company_type,
  latest_stage,
  primary_ta,
  status,
  public_private,
  ipo_date,
  country
FROM {{ source('dealforma', 'company_profiles') }}
