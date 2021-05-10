from django.db import migrations

INITIAL_MIGRATION_SQL = '''
-- Add new claim_ai_quality field to already created JsonExt's
declare 
	@CLAIM_STATUS_REJECTED INT = 1,
	@CLAIM_STATUS_ENTERED INT = 2,
	@CLAIM_STATUS_CHECKED INT = 4,
	@CLAIM_STATUS_PROCESSED INT = 8,
	@CLAIM_STATUS_VALUATED INT = 16
	
	
	
update tblClaimItems
    set JsonExt= JSON_MODIFY(
                     CONVERT (VARCHAR(MAX), JsonExt), '$.claim_ai_quality', 
                     JSON_QUERY(concat(concat('{"ai_result": "', ClaimItemStatus), '"}'))
                 ) 
    where 
        ValidityTo is null and 
        JSON_VALUE(CONVERT (VARCHAR(MAX), JsonExt), '$.claim_ai_quality.ai_result') is Null

    
update tblClaimServices
    set JsonExt= JSON_MODIFY(
                     CONVERT (VARCHAR(MAX), JsonExt), '$.claim_ai_quality', 
                     JSON_QUERY(concat(concat('{"ai_result": "', ClaimServiceStatus), '"}'))
                 ) 
    where 
        ValidityTo is null and 
        JSON_VALUE(CONVERT (VARCHAR(MAX), JsonExt), '$.claim_ai_quality.ai_result') is Null

update tblClaim
set JsonExt=case 
	when ClaimStatus = @CLAIM_STATUS_REJECTED and ValidityFromReview is not null then 
	    JSON_MODIFY(CONVERT (VARCHAR(MAX), JsonExt) ,'$.claim_ai_quality',  
	         JSON_QUERY(N'{"was_categorized": true,  "request_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'", "response_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'"}'))
	
    when ClaimStatus = @CLAIM_STATUS_REJECTED and ValidityFromReview is null then 
	     JSON_MODIFY(CONVERT (VARCHAR(MAX), JsonExt) ,'$.claim_ai_quality', 
	         JSON_QUERY(N'{"was_categorized": false, "request_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'", "response_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'"}'))
	
	-- No action on entered status
	
	when ClaimStatus = @CLAIM_STATUS_CHECKED then 
	      JSON_MODIFY(CONVERT (VARCHAR(MAX), JsonExt) ,'$.claim_ai_quality', 
	          JSON_QUERY(N'{"was_categorized": false, "request_time": "None", "response_time": "None"}'))
	
	when ClaimStatus = @CLAIM_STATUS_PROCESSED or ClaimStatus = @CLAIM_STATUS_VALUATED then 
	      JSON_MODIFY(CONVERT (VARCHAR(MAX), JsonExt), '$.claim_ai_quality',  
	          JSON_QUERY(N'{"was_categorized": true, "request_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'", "response_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'"}'))
	else JsonExt
	end
where ValidityTo is null 
and ISJSON(CONVERT (VARCHAR(MAX), JsonExt)) = 1
and JSON_VALUE(CONVERT (VARCHAR(MAX), JsonExt), '$.claim_ai_quality.was_categorized') is Null


-- Create new JsonExt field
update tblClaimItems
    set  JsonExt=concat(concat('{"claim_ai_quality": {"ai_result": "', ClaimItemStatus), '"}}') 
    where ValidityTo is null and (ISJSON(CONVERT (VARCHAR(MAX), JsonExt)) is null or ISJSON(CONVERT (VARCHAR(MAX), JsonExt)) = 0)

update tblClaimServices
    set JsonExt=concat(concat('{"claim_ai_quality": {"ai_result": "', ClaimServiceStatus), '"}}') 
    where ValidityTo is null and (ISJSON(CONVERT (VARCHAR(MAX), JsonExt)) is null or ISJSON(CONVERT (VARCHAR(MAX), JsonExt)) = 0)
	
	
update tblClaim
set JsonExt=case 
	when ClaimStatus = @CLAIM_STATUS_REJECTED and ValidityFromReview is not null then N'{"claim_ai_quality": {"was_categorized": true, "request_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'", "response_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'"}}'
	when ClaimStatus = @CLAIM_STATUS_REJECTED and ValidityFromReview is null then N'{"claim_ai_quality": {"was_categorized": false, "request_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'", "response_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'"}}'
	when ClaimStatus = @CLAIM_STATUS_ENTERED then N'{}'
	when ClaimStatus = @CLAIM_STATUS_CHECKED then N'{"claim_ai_quality": {"was_categorized": false, "request_time": "None", "response_time": "None"}}'
	when ClaimStatus = @CLAIM_STATUS_PROCESSED or ClaimStatus = @CLAIM_STATUS_VALUATED then N'{"claim_ai_quality": {"was_categorized": true, "request_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'", "response_time": "'+CONVERT(VARCHAR(30), CURRENT_TIMESTAMP, 121)+N'"}}'
	else N'{}'
	end
where ValidityTo is null and (ISJSON(CONVERT (VARCHAR(MAX), JsonExt)) is null or ISJSON(CONVERT (VARCHAR(MAX), JsonExt)) = 0)
'''


class Migration(migrations.Migration):
    dependencies = [
        ('claim', '0012_item_service_jsonExtField')
    ]

    operations = [
        migrations.RunSQL(INITIAL_MIGRATION_SQL)
    ]
