# openIMIS Backend Claim AI Quality reference module
This repository holds the files of the openIMIS Backend Claim AI Quality reference module.
It is dedicated to be deployed as a module of [openimis-be_py](https://github.com/openimis/openimis-be_py).

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## ORM mapping:
None

## Listened Django Signals
* SubmitClaimsMutation: adds 'claim_ai_quality' key to the json_ext field on claim submissions


## Services
* AiQualityReportService, loading claims used for misclassification report

## Reports (template can be overloaded via report_template.tempalte)
* miscategorisation_report

## GraphQL Queries
None

## GraphQL Mutations - each mutation emits default signals and return standard error lists (cfr. openimis-be-core_py)
None

## Additional Endpoints
* miscategorisation_report: generating report regarding ai misclassification in  PDF format


## Reports
* `miscategorisation_report`: AI Evaluation accurracy and list of misclassified claims


## Configuration options (can be changed via core.ModuleConfiguration)
  * claim_ai_url: AI Evaluation websocket endpoint, default ws://localhost:8000/api/claim_ai/ws/Claim/process/
  * event_based_activation: if False claim bundles are send as scheduled job, if True bundle of claims is sent after each submission,
  * bundle_size: number of claims in one bundle, by default 100,
  * zip_bundle: if True claim bundle is compressed before sending, claim_ai module accepts both compressed and uncompressed bundles,
  * connection_timeout: the maximum waiting time for a connection to websocket, if exceeded 
    TimeoutError is raised,
  * authentication_token: if authentication is required by server token have to be added in configuration,
  * accepted_category_code: code for claim items and services positively evaluated by AI,
  * rejected_category_code": code for claim items and services negatively evaluated by AI,
  * reason_rejected_by_ai_code: rejection code for claims rejected by AI,
  * date_format": date format used in FHIR response, by default YYYY-mm-dd

## openIMIS Modules Dependencies
* core.websocket.AsyncWebSocketClient
* core.models.ModuleConfiguration
* core.models.InteractiveUser
* core.schema.signal_mutation_module_after_mutating
* claim.models.Claim 
* claim.models.ClaimDetail  
* claim.models.ClaimItem
* claim.models.ClaimService
* claim.models.gql_mutations.SubmitClaimsMutation 
* api_fhir_r4.models.Bundle
* api_fhir_r4.models.BundleType
* api_fhir_r4.models.BundleEntry
* api_fhir_r4.serializers.ClaimSerializer
* location.models.UserDistrict
* report.services.ReportService
