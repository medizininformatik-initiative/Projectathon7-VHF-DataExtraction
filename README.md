# MII Projecathon - Data Selection, Extraction, Pseudonymisation and Bundleing

This repository combines data selection and extraction, pseudonymisation, bundleing of the extracted FHIR resources and Creating a Document Reference + Binary resource from the bundle
to be send via the DSF.

## Development use

### Step 1 Get some testdata

To get the testdata for the projectathon execute the `get-mii-testdate.sh` of this repository.
This will download the VHF testdata from the MII Github and save it to the `testdata` folder.

### Step 2 - Spin up a FHIR Server and load it with data

To spin up a FHIR server clone the following repository: https://github.com/medizininformatik-initiative/fhir-server-examples
navigate to the server/blaze folder and execute `docker-compose -p mii-projectathon up -d`
This will spin up blaze FHIR server and expose it on localhost on port 8081.
You can access your FHIR server under <http://localhost:8081/fhir/my-endpoint-here> , to see all your currently loaded Patients go to:
<http://localhost:8081/fhir/Patient>

Once the server is available (this can take a couple of seconds) and you get a response from the Patient URL above you can load your testdata.

To load your testdata execute `upload-testdata.sh`, which will upload all the testdate fromt the `testdata` folder to your FHIR server.

Once the script is finished access <http://localhost:8081/fhir/Patient> again to see if your resources have been loaded.


### Step 3 - Create local version of config files

Create your own config files using the `initialise-env-files.sh`

### Step 4 - Run the data extraction, pseudonymisation and bundleing

In this repository execute  `docker-compose -p mii-projectathon up`
This will run in sequence the three python scripts of this repository:

1. data-selection-and-extraction.py   (selects and extracts the data according to the data_extraction_config.json) - see section data-selection-and-extraction.py below)
2. pseudonymisation.py (pseudonymises selected resources according to the psd_config.json  - see section pseudonymisation.py below)
3. build-transaction-bundle.py (bundles all extracted resources into one single transaction bundle, b64 encodes it and creates another Transaction bundle which contains a DocumentReference FHIR resource and a Binary FHIR resources which includes the b64 encoded bundle created before)

All scripts create files:
(1.) saves all extracted reources in `extracted_resources`
(2.) saves all pseudonymised resources in `pseudonymised_resources`
(3.) saves the extracted resources bundle, the b64 of the extracted resources bundle and the bundle for the base64 extracted resources bundle in `to_send`

# Running each script individually

## data-selection-and-extraction.py

To see the available script arguments execute `python3 data-selection-and-extraction.py -h`

This script selects and extracts data from a FHIR server according to the data_extraction_config.json

|field|description|possible values|default value should be|
|-|-|-|-|
|name|name of the data extraction - used to specify the filename use for this data extrcation|||
|query|query used to extract the data - |any fhir search string which return only one resource type|
|output_file_path|path where to save the extracted resources|any path to a folder - best left as extracted_resources||
|request_type|How should data be extracted - with a POST or a GET request|POST , GET| GET|
|cohort_extraction|specifies that a cohort should be extracted from this fhir search extraction - contains two subfields cohort_id_field and cohort_id_prefix both of which are required if cohort_extraction is used ||
|cohort_id_field| the json path to the field which contains the patient ids of this resource||
|cohort_id_prefix| the id prefix which has to be deleted to get the actual IDs||
|cohort_dependence| specifies that an extraction is to be cohort dependen - contains two subfields chunk_size and cohort_id_selection_field both of which are required if cohort_extraction is used ||
|chunk_size|defines the chunks into which ids are meant to be split when extracted the resources according to the cohort||
|cohort_id_selection_field| the fhir search param to be used to select the cohort ||


## pseudonymisation.py

To see the available script arguments execute `python3 pseudonymisation.py -h`

This script pseudonymises FHIR resources according to the psd_config.json


|field|description|possible values|default value should be|
|-|-|-|-|
|psd_name| name of the pseudonymisation - used to specify the filename used to save this pseudonymised data and the filename for the file from wich the resources to be pseudonymised are loaded |||
|input_file_path|path from which to load the resources to be pseudonymised |any path to a folder - best left as extracted_resources||
|psd_file_path|path where pseudonymised resources are to be saved  - best left as pseudonymised_resources|||
|select|List of paths to parts of a FHIR resource to be selected into the new pseudonymised resources e.g. "id" - path logic see below this table |||
|change_id|List of ids to replace - contains two subfields id_pool and path_to_id both of which are required if change_id is used|||
|id_pool| the pool of pseudonyms the pseudonym is part of - this ensures that the same Ids are replaced with the same PSD ids|||
|path_to_id| path to the field where to replace the id - path logic see below this table|||
|apply_function| applies a pseudonymisation function to a field note that these have to be implemented in the pseudonymisation.py to be available here - contains two subfields function_to_apply and path_to_field both of which are required if apply_function is used|||
|function_to_apply| specifies the function to apply to a field|||
|path_to_field| path to the field which the function is to be applied to - path logic see below this table|||


path logic for pseudonymisation:
<field_name or array>.<field_name or array>.<field_name or array>
Array can be with index [0] or [*] to apply to all entries in array, examples:
"id",
"resourceType",
"diagnosis.[*].use",
"serviceType",
"diagnosis.[*].condition.reference",
"subject.reference",
"period"

Note - more complex paths are currently not supported


available pseudonymisation functions:
obfuscate_date_to_year, obfuscate_date_to_day


## build-transaction-bundle.py

To see the available script arguments execute `python3 build-transaction-bundle.py -h`