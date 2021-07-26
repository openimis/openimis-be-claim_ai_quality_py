adjudication_bundle = {
    'resourceType': 'AdjudicationBundle',
    'entry': [
        {
            'fullUrl': 'localhost',
            'resource': {
                "resourceType": 'ClaimResponse',
                "status": 'active',
                "type": {'text': "R"},
                "outcome": 'complete',
                "insurer": {
                    "reference": "Organization/openIMIS-Claim-AI"
                },
                "id": "C670E61A-36F1-4F70-A5D2-6CE2C20457F6",
                "item": [
                    {
                        "adjudication": [
                            {
                                "amount": {
                                    "currency": "$",
                                    "value": 13.0
                                },
                                "category": {
                                    "coding": [
                                        {
                                            "code": "-2",
                                        }
                                    ],
                                    "text": "AI"
                                },
                                "reason": {
                                    "coding": [
                                        {
                                            "code": 0
                                        }
                                    ],
                                    "text": "accepted"
                                },
                                "value": 1.0
                            }
                        ],
                        "extension": [
                            {
                                "url": "Medication",
                                "valueReference": {
                                    "reference": "Medication/4DAFEF84-7AFA-47C6-BB51-B6D5511A8AF9"
                                }
                            }
                        ],
                        "itemSequence": 1,
                        "noteNumber": [
                            1
                        ]
                    },
                    {
                        "adjudication": [
                            {
                                "amount": {
                                    "currency": "$",
                                    "value": 400.0
                                },
                                "category": {
                                    "coding": [
                                        {
                                            "code": "-2",
                                        }
                                    ],
                                    "text": "AI"
                                },
                                "reason": {
                                    "coding": [
                                        {
                                            "code": 1
                                        }
                                    ],
                                    "text": "rejected"
                                },
                                "value": 1.0
                            }
                        ],
                        "outcome": "complete",
                        "extension": [
                            {
                                "url": "ActivityDefinition",
                                "valueReference": {
                                    "reference": "Medication/48DB6423-E696-45D9-B76E-CA1B7C57D738"
                                }
                            }
                        ],
                        "itemSequence": 2,
                        "noteNumber": [
                            2
                        ]
                    }
                ],
                "use": "claim"
            }
        }
    ]
}


def custom_bundle(claim_id, item_id, service_id):
    bundle = adjudication_bundle.copy()
    claim = bundle['entry'][0]['resource']
    claim['id'] = claim_id
    claim['item'][0]['extension'][0]['valueReference']['reference'] = F'Medication/{item_id}'
    claim['item'][1]['extension'][0]['valueReference']['reference'] = F'ActivityDefinition/{service_id}'
    bundle['entry'][0]['resource'] = claim
    return bundle
