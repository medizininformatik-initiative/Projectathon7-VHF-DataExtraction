#!/bin/bash

FHIR_BASE_URL=${FHIR_BASE_URL:-"http://fhir-server:8080/fhir"}
ORG_IDENT=${ORG_IDENT:-"my-org-ident"}
PSD_NAMES=${PSD_NAMES:-"pats,enc,obs,cond"}
PSD_DATE_TIME=$(date +"%Y-%m-%d_%H-%M-%S")

# TODO add if to set own certs
CA_FILE="/opt/data-extraction/certs/custom-ca-bundle.crt"
if [ -f "$CA_FILE" ]; then
    export REQUESTS_CA_BUNDLE="$CA_FILE"
fi

echo "Begin extracting data at time $PSD_DATE_TIME..."
python3 data-selection-and-extraction.py --fhirurl "$FHIR_BASE_URL" --fhiruser "$FHIR_USER" \
--fhirpw "$FHIR_PW" --fhirtoken $FHIR_TOKEN --httpproxyfhir "$FHIR_PROXY_HTTP" --httpsproxyfhir "$FHIR_PROXY_HTTPS"
echo "Finished extracting data"

echo "Begin pseudonymising data..."
python3 pseudonymisation.py --psddatetime "$PSD_DATE_TIME"
echo "Finished pseudonymising data"

echo "Begin creation of extraction transfer bundle..."
python3 build-transaction-bundle.py --fhirurl "$SHARE_FHIR_BASE_URL" --fhiruser "$SHARE_FHIR_USER" \
--fhirpw "$SHARE_FHIR_PW" --fhirtoken $SHARE_FHIR_TOKEN --httpproxyfhir "$SHARE_FHIR_PROXY_HTTP" --httpsproxyfhir "$SHARE_FHIR_PROXY_HTTPS" \
--orgident "$ORG_IDENT" --psddatetime "$PSD_DATE_TIME" --psdnames "$PSD_NAMES" $STORE_BUNDLE $ENCB64 --projectident "$PROJ_IDENT"
echo "Finished creation of extraction transfer bundle..."

echo "Goodbye - have a nice day"
