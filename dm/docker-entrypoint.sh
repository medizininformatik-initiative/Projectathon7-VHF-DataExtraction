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

echo "Begin downloading and decoding and uploading bundles $PSD_DATE_TIME..."
python3 download-decode-upload.py --fhirurl "$FHIR_BASE_URL" --fhiruser "$FHIR_USER" \
--fhirpw "$FHIR_PW" --fhirtoken $FHIR_TOKEN --httpproxyfhir "$FHIR_PROXY_HTTP" --httpsproxyfhir "$FHIR_PROXY_HTTPS" \
--projectident "$PROJ_IDENT"  --npatsbundle "$N_PATS_BUNDLE" $SEND_TO_FHIR
echo "Finished extracting data"
