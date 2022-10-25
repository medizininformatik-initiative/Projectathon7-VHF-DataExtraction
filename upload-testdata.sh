#!/usr/bin/env bash

BASE_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 || exit 1 ; pwd -P )"
FHIR_BASE_URL=${FEASIBILITY_TESTDATA_UPLOAD_FHIR_BASE_URL:-http://localhost:8081/fhir}

FILES=("$BASE_DIR"/testdata/*)
count=0
for fhirBundle in "${FILES[@]}"; do
  echo "Sending Testdata bundle $fhirBundle ..."
  curl -X POST -H "Content-Type: application/json" -d @"$fhirBundle" "$FHIR_BASE_URL"
  count=$((count + 1))
  echo $count
  if [[ "$count" -eq 1000 ]]
  then
    count=0
    sleep 5
  fi
done
