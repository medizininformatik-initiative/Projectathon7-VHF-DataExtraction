import requests
import argparse
from requests.auth import HTTPBasicAuth
from json.decoder import JSONDecodeError
from urllib.parse import urlparse
from urllib.parse import parse_qs
from jsonpath_ng.ext import parse

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


chunk_size = 100

# Get all  NTproBNP Observations between 01.01.2019 und 31.12.2021
query = "/Observation?code=http://loinc.org%7C33763-4,http://loinc.org%7C71425-3,http://loinc.org%7C33762-6,http://loinc.org%7C83107-3,http://loinc.org%7C83108-1,http://loinc.org%7C77622-9,http://loinc.org%7C77621-1&date=ge2019-01-01&date=le2021-12-31&_format=json"
obs_list = get_all_res_for_query(query)

# get Pats and Cohort Pat Ids
pat_ids = extract_ids_from_resources(obs_list, "subject.reference", "Patient/")
pat_list = []
for chunk in chunks(pat_ids, chunk_size):
    query = f'/Patient?_id={",".join(chunk)}'
    pat_list = pat_list + get_all_res_for_query(query, False)

# Get Encs for cohort of type Einrichtungskontakt
enc_list = []
for chunk in chunks(pat_ids, chunk_size):
    query = f'/Encounter?subject={",".join(chunk)}&type=einrichtungskontakt'
    enc_list = enc_list + get_all_res_for_query(query, False)


# Get Conds for cohort
cond_list = []
for chunk in chunks(pat_ids, chunk_size):
    query = f'/Condition?subject={",".join(chunk)}'
    cond_list = get_all_res_for_query(query, False)
