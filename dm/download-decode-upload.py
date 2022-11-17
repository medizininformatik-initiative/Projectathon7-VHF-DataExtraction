import json
import base64
import requests
import argparse
from requests.auth import HTTPBasicAuth

parser = argparse.ArgumentParser()
parser.add_argument('--fhirurl', help='base url of your local fhir server',
                    default="http://localhost:8082/fhir")
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
parser.add_argument(
    '--sendtofhir', help='boolean whether to store the bundle in the local fhir server', action='store_true', default=False)
parser.add_argument(
    '--npatsbundle', help='token auth fhir server', nargs="?", type=int, default=1000)
parser.add_argument(
    '--projectident', help='project identifier', nargs="?", default="NT-proBNP")

args = vars(parser.parse_args())

fhir_base_url = args["fhirurl"]
fhir_user = args["fhiruser"]
fhir_pw = args["fhirpw"]
fhir_token = args["fhirtoken"]
http_proxy_fhir = args["httpproxyfhir"]
https_proxy_fhir = args["httpsproxyfhir"]
send_to_fhir = args["sendtofhir"]
n_pats_bundle = args["npatsbundle"]
project_ident = args["projectident"]

proxies_fhir = {
    "http": http_proxy_fhir,
    "https": https_proxy_fhir
}


def get_b64_enc_bundle(binary_url):

    fhir_query = f'{fhir_base_url}/{binary_url}'
    if fhir_token is not None:
        resp = requests.get(fhir_query, headers={
                            'Authorization': f"Bearer {fhir_token}"}, proxies=proxies_fhir)
    else:
        resp = requests.get(fhir_query, auth=HTTPBasicAuth(
            fhir_user, fhir_pw), proxies=proxies_fhir)

    resp_json = resp.json()

    b64_string = resp_json["data"]

    return b64_string


def get_pat_id_by_resource_type(resource, resource_type):

    if resource_type == "Patient":
        return resource["id"]

    return resource["subject"]["reference"].split("/")[1]


def get_bucket_index_for_id(id, bucket_id_list):

    for bucket_index in range(0, len(bucket_id_list)):
        bucket = bucket_id_list[bucket_index]
        if len(bucket) < bucket_size:
            bucket.append(id)
            return bucket_index

    bucket_id_list.append([id])
    return len(bucket_id_list) - 1


def download_split_bundle_and_upload(bundle_string, bundle_id):

    id_to_bucket = {}
    bucket_id_list = []
    bundle_list = []

    fhir_bundle = json.loads(bundle_string)

    for entry in fhir_bundle["entry"]:

        pat_id = get_pat_id_by_resource_type(
            entry["resource"], entry["resource"]["resourceType"])

        if pat_id not in id_to_bucket:
            bucket_index = get_bucket_index_for_id(pat_id, bucket_id_list)
            id_to_bucket[pat_id] = bucket_index

        if id_to_bucket[pat_id] >= len(bundle_list):
            new_bundle = {
                "resourceType": "Bundle",
                "type": "transaction",
                "entry": []
            }
            bundle_list.append(new_bundle)

        bundle_list[id_to_bucket[pat_id]]["entry"].append(entry)

    output_file_path = "split_insert_bundles"

    for index in range(0, len(bundle_list)):
        with open(f'{output_file_path}/bundle_{str(bundle_id)}_{str(index)}.json', 'w') as f:
            json.dump(bundle_list[index], f)

        if send_to_fhir:
            if fhir_token is not None:
                resp = requests.post(fhir_base_url, headers={
                    'Authorization': f"Bearer {fhir_token}"}, proxies=proxies_fhir, json=bundle_list[index])

                print(resp.status_code)
                print(resp.content)
            else:
                resp = requests.post(fhir_base_url, auth=HTTPBasicAuth(
                    fhir_user, fhir_pw), proxies=proxies_fhir, json=bundle_list[index])

                print(resp.status_code)
                print(resp.content)


def get_list_of_bundles(project_ident):
    fhir_query = f'{fhir_base_url}/DocumentReference?identifier=http://medizininformatik-initiative.de/sid/project-identifier|{project_ident}'
    bundle_list = []
    if fhir_token is not None:
        resp = requests.get(fhir_query, headers={
                            'Authorization': f"Bearer {fhir_token}"}, proxies=proxies_fhir)
    else:
        resp = requests.get(fhir_query, auth=HTTPBasicAuth(
            fhir_user, fhir_pw), proxies=proxies_fhir)

    resp_json = resp.json()

    for entry in resp_json["entry"]:
        new_bundle_url = entry["resource"]["content"][0]["attachment"]['url']

        if entry["resource"]["content"][0]["attachment"]["contentType"] == "text/plain":
            bundle_list.append(new_bundle_url)

    return bundle_list


bucket_size = n_pats_bundle
bundle_list = get_list_of_bundles(project_ident)

for index in range(0, len(bundle_list)):
    bundle_url = bundle_list[index]
    b64_string = get_b64_enc_bundle(bundle_url)
    bundle_string = base64.b64decode(b64_string)
    download_split_bundle_and_upload(bundle_string, index)
