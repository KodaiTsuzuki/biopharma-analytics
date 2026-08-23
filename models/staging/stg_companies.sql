SELECT 
  company_id,
  name,
  company_type,
  country
FROM {{ source('dealforma', 'companies') }}

