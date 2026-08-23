SELECT 
  deal_id,
  deal_title,
  licensor_id,
  licensee_id,
  announced_date,
  deal_year,
  ta_id,
  type_id,
  stage_id,
  total_value_m,
  upfront_cash_m,
  total_milestones_m,
  deal_size_bucket,
  rare_disease,
  ai_deal,
  deal_status
FROM {{ source('dealforma', 'deals') }}
