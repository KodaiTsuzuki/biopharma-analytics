SELECT 
  ta_id,
  name
FROM {{ source('dealforma', 'therapeutic_areas') }}
