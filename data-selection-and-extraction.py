import requests
import argparse
from requests.auth import HTTPBasicAuth
from json.decoder import JSONDecodeError
from urllib.parse import urlparse
from urllib.parse import parse_qs
from jsonpath_ng.ext import parse
import json

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

        if post_query is True:
            parsed_url = urlparse(query_url)
            params = parse_qs(parsed_url.query)
            payload = {}
            for param in params:
                payload[param] = params[param]
            search_url = f'{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}/_search'
            resp = requests.post(search_url, headers={'Authorization': f"Bearer {fhir_token}"},
                                 data=payload, proxies=proxies_fhir)
        else:
            resp = requests.get(query_url, headers={'Authorization': f"Bearer {fhir_token}"},
                                proxies=proxies_fhir)
    else:
        if post_query is True:
            parsed_url = urlparse(query_url)
            params = parse_qs(parsed_url.query)
            payload = {}
            for param in params:
                payload[param] = params[param]

            search_url = f'{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}/_search'
            resp = requests.post(search_url, auth=HTTPBasicAuth(
                fhir_user, fhir_pw), data=payload, proxies=proxies_fhir)
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

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


with open("data_extraction_config.json", "r") as f:
    data_extraction_config = json.load(f)

extracted_resources = {}
cohort_ids = []

for extraction in data_extraction_config:
    extraction_name = extraction['name']
    output_file_path = extraction['output_file_path']
    query = extraction['query']
    extracted_res_list = []

    if "cohort_dependence" in extraction:
        cohort_id_field = extraction['cohort_dependence']['cohort_id_selection_field']
        append_prefix = "&"
        if "?" not in query:
            append_prefix = "?"

        chunk_size = extraction['cohort_dependence']['chunk_size']
        
        for chunk in chunks(cohort_ids, chunk_size):
            temp_query = f'{query}{append_prefix}{cohort_id_field}={",".join(chunk)}&_count=500'
            print(f'Extracting chunk with query {temp_query}')
            extracted_res_list = extracted_res_list + get_all_res_for_query(temp_query, False)

    else:
        extracted_res_list = get_all_res_for_query(query)

    print(f'Extracted {len(extracted_res_list)} resources for extraction with name {extraction_name}')
    extracted_resources[extraction_name] = extracted_res_list

    if "cohort_extraction" in extraction:
        cohort_id_field = extraction['cohort_extraction']['cohort_id_field']
        cohort_id_prefix = extraction['cohort_extraction']['cohort_id_prefix']
        part_cohort_ids = extract_ids_from_resources(extracted_res_list, cohort_id_field, cohort_id_prefix)
        cohort_ids = cohort_ids + part_cohort_ids

    with open(f'{output_file_path}/{extraction_name}.json', 'w') as f:
        json.dump(extracted_resources[extraction_name], f)
