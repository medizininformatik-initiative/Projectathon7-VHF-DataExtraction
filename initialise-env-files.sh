#!/bin/bash

envfiles=( ".env" "data_extraction_config.json" "psd_config.json")

for file in "${envfiles[@]}"
do
  if [[ -f "$file" ]]; then
    printf "file %s already exists - not copying default env \n" "$file"
    printf "Please check if your current env file %s is missing any params from the %s file and copy them as appropriate\n\n" "$file" "$file.default"
  else
    cp "$file.default" "$file"
  fi
done
