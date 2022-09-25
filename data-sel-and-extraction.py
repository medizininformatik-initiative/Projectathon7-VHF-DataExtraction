import requests
import json
import argparse
from datetime import datetime, date
from requests.auth import HTTPBasicAuth
from json.decoder import JSONDecodeError
from urllib.parse import urlparse
from urllib.parse import parse_qs
import pandas as pd
from jsonpath_ng.ext import parse
import uuid
import re

parser = argparse.ArgumentParser()
parser.add_argument('--fhirurl', help='base url of your local fhir server',
                    default="http://localhost:8081/fhir")
parser.add_argument(
    '--fhiruser', help='basic auth user fhir server', nargs="?", default="")
parser.add_argument(
    '--fhirpw', help='basic auth pw fhir server', nargs="?", default="")
parser.add_argument(
    '--fhirtoken', help='token auth fhir server', nargs="?", default=None)
parser.add_argument(
    '--httpproxyfhir', help='http proxy url for your fhir server - None if not set here', nargs="?", default=None)
parser.add_argument('--httpsproxyfhir',
                    help='https proxy url for your fhir server - None if not set here', nargs="?", default=None)

args = vars(parser.parse_args())

fhir_base_url = args["fhirurl"]
fhir_user = args["fhiruser"]
fhir_pw = args["fhirpw"]
fhir_token = args["fhirtoken"]
http_proxy_fhir = args["httpproxyfhir"]
https_proxy_fhir = args["httpsproxyfhir"]

proxies_fhir = {
    "http": http_proxy_fhir,
    "https": https_proxy_fhir
}


def execute_query(query, post_query=False):

    query_url = f'{fhir_base_url}{query}'
    if fhir_token is not None:
        resp = requests.get(query_url, headers={'Authorization': f"Bearer {fhir_token}"},
                            proxies=proxies_fhir)
    else:
        resp = requests.get(query_url, auth=HTTPBasicAuth(
            fhir_user, fhir_pw), proxies=proxies_fhir)

    resp_object = {}
    resp_object['status'] = "success"

    if resp.status_code != 200:
        resp_object['status'] = "failed"

    try:
        resp_object['json'] = resp.json()
    except JSONDecodeError:
        resp_object['status'] = "failed"

    return resp_object


def get_next_link(link_elem):
    for elem in link_elem:
        if elem['relation'] == 'next':
            return elem['url']

    return None


def page_through_results_and_collect(resp_json, results):

    if 'entry' not in resp_json:
        return results

    next_link = get_next_link(resp_json['link'])
    results = list(map(lambda entry: entry['resource'], resp_json['entry']))

    while next_link:
        if fhir_token is not None:
            resp = requests.get(next_link, headers={'Authorization': f"Bearer {fhir_token}"},
                                proxies=proxies_fhir)
        else:
            resp = requests.get(next_link, auth=HTTPBasicAuth(
                                fhir_user, fhir_pw), proxies=proxies_fhir)

        next_link = get_next_link(resp.json()['link'])
        results = results + \
            list(map(lambda entry: entry['resource'], resp.json()['entry']))

    return results


def get_all_res_for_query(query, post_query=False):
    resp = execute_query(query, post_query)
    resp_json = resp['json']
    resources = []
    return page_through_results_and_collect(resp_json, resources)


def extract_ids_from_resources(resource_list, extraction_path, id_prefix):

    jsonpath_expression = parse(extraction_path)
    id_list = []

    for resource in resource_list:
        references_found = jsonpath_expression.find(resource)
        for match in references_found:
            id_list.append(str(match.value).replace(id_prefix, ""))

    return id_list


def remove_from_object_by_expression(to_remove, resource):
    jsonpath_expression = parse(to_remove)

    found = jsonpath_expression.find(resource)
    for match in found:
        path = [str(match.path)]
        match = match.context

        while match.context is not None:
            path = [str(match.path)] + path
            match = match.context

        for index in range(0, len(path) - 1):
            cur_key = path[index]
            if "[" in cur_key:
                cur_key = re.sub(r"[\[\]]", "", cur_key)
                cur_key = int(cur_key)
            resource = resource[cur_key]

        del resource[path[len(path)-1]]

def change_id_in_obj_by_expression(id_change, resource):

    jsonpath_expression = parse(id_change['path_to_id'])
    id_pool = id_change['id_pool']
    id_prefix = id_change.get('id_prefix', None)
    found = jsonpath_expression.find(resource)
    for match in found:
        path = [str(match.path)]
        match = match.context

        while match.context is not None:
            path = [str(match.path)] + path
            match = match.context

        for index in range(0, len(path) - 1):

            cur_key = path[index]
            if "[" in cur_key:
                cur_key = re.sub(r"[\[\]]", "", cur_key)
                cur_key = int(cur_key)

            resource = resource[cur_key]

        cur_id = resource[path[len(path) - 1]]
        
        if id_prefix is not None:
            cur_id = cur_id.replace(id_prefix, "")

        if cur_id not in id_pool:
            psd_id = str(uuid.uuid4())
            id_pool[cur_id] = psd_id
        else:
            psd_id = id_pool[cur_id]

        if id_prefix is not None:
            resource[path[len(path) - 1]] = f'{id_prefix}{psd_id}'
        else:
            resource[path[len(path) - 1]] = psd_id


def pseudonomise_resource(resource, psd_config):

    for id_change in psd_config['change_id']:
        # print(f'Changing ids for expression: {id_change["path_to_id"]}')
        change_id_in_obj_by_expression(id_change, resource)
      
    for to_remove in psd_config['remove']:
        remove_from_object_by_expression(to_remove, resource)

    return resource

def pseudonomise_resources(resource_list, psd_config):
    psd_resources = []

    for resource in resource_list:
        psd_resources.append(pseudonomise_resource(resource, psd_config))

    return psd_resources


# Get all  NTproBNP Observations between 01.01.2019 und 31.12.2021
query = "/Observation?code=http://loinc.org%7C33763-4,http://loinc.org%7C71425-3,http://loinc.org%7C33762-6,http://loinc.org%7C83107-3,http://loinc.org%7C83108-1,http://loinc.org%7C77622-9,http://loinc.org%7C77621-1&date=ge2019-01-01&date=le2021-12-31&_format=json"
obs_list = get_all_res_for_query(query)

# get Pats and Cohort Pat Ids
pat_ids = extract_ids_from_resources(obs_list, "subject.reference", "Patient/")
query = f'/Patient?id={",".join(pat_ids)}'
pat_list = get_all_res_for_query(query, True)

# Get Encs for cohort of type Einrichtungskontakt
query = f'/Encounter?subject={",".join(pat_ids)}&type=einrichtungskontakt'
enc_list = get_all_res_for_query(query, True)

# Get Conds for cohort
query = f'/Condition?subject={",".join(pat_ids)}'
cond_list = get_all_res_for_query(query, True)


obs_id_pseudonyms = {}
pat_id_pseudonyms = {}
enc_id_pseudonyms = {}
cond_id_pseudonyms = {}

# Pseudonymise obs
psd_config = {
    "remove": ["meta"],
    "change_id": [
        {
            "id_pool": obs_id_pseudonyms,
            "path_to_id": "id"
        },
        {
            "id_pool": pat_id_pseudonyms,
            "id_prefix": "Patient/",
            "path_to_id": "subject.reference"
        },
        {
            "id_pool": enc_id_pseudonyms,
            "id_prefix": "Encounter/",
            "path_to_id": "encounter.reference"
        },
        {
            "id_pool": obs_id_pseudonyms,
            "path_to_id": "$.identifier[?system = 'https://VHF.de/befund'].value"
        }
    ]
}

print("Begin pseudonomysation of Observations...")
#obs_list = obs_list[0:0]
with open('extracted_resources/obs.json', 'w') as f:
    json.dump(obs_list, f)
psd_obs = pseudonomise_resources(obs_list, psd_config)
print("End pseudonomysation...")
with open('extracted_resources/psd-obs.json', 'w') as f:
    json.dump(psd_obs, f)


# Pseudonymise pats
psd_config = {
    "remove": ["name", "address"],
    "change_id": [
        {
            "id_pool": pat_id_pseudonyms,
            "path_to_id": "id"
        },
        {
            "id_pool": pat_id_pseudonyms,
            "path_to_id": "$.identifier[?system = 'https://VHF.de/pid'].value"
        }
    ]
}

print("Begin pseudonomysation of Patients...")
#pat_list = pat_list[0:0]
with open('extracted_resources/pats.json', 'w') as f:
    json.dump(pat_list, f)
psd_pats = pseudonomise_resources(pat_list, psd_config)
print("End pseudonomysation...")
with open('extracted_resources/psd-pats.json', 'w') as f:
    json.dump(pat_list, f)


# Pseudonymise enc
psd_config = {
    "remove": ["meta"],
    "change_id": [
        {
            "id_pool": enc_id_pseudonyms,
            "path_to_id": "id"
        },
        {
            "id_pool": cond_id_pseudonyms,
            "id_prefix": "Condition/",
            "path_to_id": "diagnosis[*].condition.reference"
        },
        {
            "id_pool": pat_id_pseudonyms,
            "id_prefix": "Patient/",
            "path_to_id": "subject.reference"
        },
        {
            "id_pool": enc_id_pseudonyms,
            "path_to_id": "$.identifier[*].value"
        }
    ]
}

print("Begin pseudonomysation of Encounters...")
# enc_list = enc_list[0:0]
with open('extracted_resources/enc.json', 'w') as f:
    json.dump(enc_list, f)
psd_pats = pseudonomise_resources(enc_list, psd_config)
print("End pseudonomysation...")
with open('extracted_resources/psd-encs.json', 'w') as f:
    json.dump(enc_list, f)


# Pseudonymise cond
psd_config = {
    "remove": ["meta"],
    "change_id": [
        {
            "id_pool": cond_id_pseudonyms,
            "path_to_id": "id"
        },
        {
            "id_pool": pat_id_pseudonyms,
            "id_prefix": "Patient/",
            "path_to_id": "subject.reference"
        },
        {
            "id_pool": enc_id_pseudonyms,
            "path_to_id": "$.identifier[*].value"
        }
    ]
}

print("Begin pseudonomysation of Conditions...")
# cond_list = cond_list[0:4]
with open('extracted_resources/cond.json', 'w') as f:
    json.dump(cond_list, f)
psd_pats = pseudonomise_resources(cond_list, psd_config)
print("End pseudonomysation...")
with open('extracted_resources/psd-conds.json', 'w') as f:
    json.dump(cond_list, f)

with open('extracted_resources/psd-obs-ids.json', 'w') as f:
    json.dump(obs_id_pseudonyms, f)

with open('extracted_resources/psd-pat-ids.json', 'w') as f:
    json.dump(pat_id_pseudonyms, f)

with open('extracted_resources/psd-enc-ids.json', 'w') as f:
    json.dump(enc_id_pseudonyms, f)

with open('extracted_resources/psd-cond-ids.json', 'w') as f:
    json.dump(cond_id_pseudonyms, f)

