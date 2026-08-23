SELECT 
  id,
  company_uuid,
  investor_name
FROM {{ source('dealforma', 'company_investors') }}
