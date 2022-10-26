#!/bin/bash

FHIR_BASE_URL=${FHIR_BASE_URL:-"http://fhir-server:8080/fhir"}
BROKER_ENDPOINT_URI=${BROKER_ENDPOINT_URI:-"http://aktin-broker:8080/broker/"}
CLIENT_AUTH_PARAM=${CLIENT_AUTH_PARAM:-"xxxApiKey123"}
ORG_IDENT=${ORG_IDENT:-"my-org-ident"}
PSD_NAMES=${PSD_NAMES:-"pats,enc,obs,cond"}
PSD_DATE_TIME=$(date +"%Y-%m-%d_%H-%M-%S")

echo "Begin extracting data at time $PSD_DATE_TIME..."
python3 data-selection-and-extraction.py --fhirurl $FHIR_BASE_URL --fhiruser $FHIR_USER \
--fhirpw $FHIR_PW --fhirtoken $FHIR_TOKEN --httpproxyfhir $FHIR_PROXY_HTTP --httpsproxyfhir $FHIR_PROXY_HTTPS
echo "Finished extracting data"

echo "Begin pseudonymising data..."
python3 pseudonymisation.py --psddatetime $PSD_DATE_TIME
echo "Finished pseudonymising data"

echo "Begin creation of extraction transfer bundle..."
python3 build-transaction-bundle.py --fhirurl $FHIR_BASE_URL --fhiruser $FHIR_USER \
--fhirpw $FHIR_PW --fhirtoken $FHIR_TOKEN --httpproxyfhir $FHIR_PROXY_HTTP --httpsproxyfhir $FHIR_PROXY_HTTPS \
--orgident "$ORG_IDENT" --psddatetime $PSD_DATE_TIME --psdnames "$PSD_NAMES" $STORE_BUNDLE $ENCB64
echo "Finished creation of extraction transfer bundle..."

echo "Goodbye - have a nice day"
