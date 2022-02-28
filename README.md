# openIMIS Backend Claim AI Quality reference module
This repository holds the files of the openIMIS Backend Claim AI Quality reference module.
It is dedicated to be deployed as a module of [openimis-be_py](https://github.com/openimis/openimis-be_py).

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## ORM mapping:
None

## Listened Django Signals
#### SubmitClaimsMutation 
Adds 'claim_ai_quality' key to the json_ext field on claim submissions.  
If ClaimAiQualityConfig.event_based_activation is set to true AI adjudication is performed.
#### EvaluateByAIMutation
Adjudication is called using `after_claim_ai_evaluation_validation` signal.


## Services
* AiQualityReportService, loading claims used for misclassification report

## Reports
* #### miscategorisation_report

## GraphQL Queries
None

## GraphQL Mutations
#### EvaluateByAIMutation
Used for manual AI Adjudication of selected claims through `after_claim_ai_evaluation_validation` signal. 
`gql_mutation_submit_claims_perms` permission required. 

## Additional Endpoints
* miscategorisation_report: generating report regarding ai misclassification in  PDF format


## Reports
* `miscategorisation_report`: AI Evaluation accurracy and list of misclassified claims


## Configuration options (can be changed via core.ModuleConfiguration)
#### Rest API Configuration
* `rest_api_login_endpoint`: Endpoint used for getting user authentication token.   
Default: `http://localhost:8000/api/api_fhir_r4/login/`,
* `rest_api_bundle_evaluation_endpoint`: Endpoint used for sending bundle of claims for evaluation.  
Default: `http://localhost:8000/api/claim_ai/claim_bundle_evaluation/`,
* `rest_api_single_claim_evaluation_endpoint`: Endpoint used for sending single claim for evaluation.  
Default: `http://localhost:8000/api/claim_ai/claim_evaluation/`,
* `wait_for_evaluation`: If set to `False` system doesn't wait for server response and have to use other method to 
pull adjudication data. 
* `rest_api_user_login`: Username of user used for AI Server JWT Authentication.
* `rest_api_user_password`: Username of user used for AI Server JWT Authentication.
#### Remaining 
* `claim_ai_username`: User dedicated to perform DB operations executed in background by Claim AI Quality module.
By default it's `_ClaimAIAdmin` added in module migration.
* `event_based_activation`: Determines if AI evaluation should be done on claim submission (`True`) or 
using scheduled job (`True`). Default: `False`
* bundle_size: number of claims in one bundle if scheduled job is used. Default: `200`,
* `accepted_category_code`: Code for Items/Services positively evaluated by AI. Default: `0`,
* `rejected_category_code`: Code for Items/Services negatively evaluated by AI. Default: `1`,
* `reason_rejected_by_ai_code`: FHIR Rejection reason code for claims rejected by AI. Default: `-2`,
* `date_format`: date format used in FHIR response. Default: `%Y-%m-%d`,
* `misclassification_report_perms`: List of permissions required to get Misclassification report.  
Default: [`112001`],
* `evaluation_method`: Method used for AI evaluation. If set to `rest_api` claims are adjudicated using 
REST API connection. If set to `integrated` then system is using `claim_ai` module installed on same instance
as Claim AI Quality server.  
Default: (empty string). - if `claim_ai` module is installed locally it uses this module. If it's 
not installed REST API is used.  

## openIMIS Modules Dependencies
* core
* claim
* api_fhir_r4
* location
* report
