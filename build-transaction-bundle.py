import json
import base64
import uuid
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
    '--storebundle', help='boolean whether to store the bundle in the local fhir server', action='store_true', default=False)
parser.add_argument(
    '--encb64', help='boolean whether to encode the transfer bundle b64 or not', action='store_true', default=False)
parser.add_argument(
    '--orgident', help='identifier of your organisation', nargs="?", default="my-org-ident")
parser.add_argument(
    '--psddatetime', help='time of pseudonmised resources to use format: 2022-09-26_10-03-40', nargs="?", default="2022-09-26_10-03-40")
parser.add_argument(
    '--psdnames', help='comma separated list of extraction names - see psd_name of psd_config.json', nargs="?", default="pats,enc,obs,cond")

args = vars(parser.parse_args())

fhir_base_url = args["fhirurl"]
fhir_user = args["fhiruser"]
fhir_pw = args["fhirpw"]
fhir_token = args["fhirtoken"]
http_proxy_fhir = args["httpproxyfhir"]
https_proxy_fhir = args["httpsproxyfhir"]
send_transaction_bundle = args["storebundle"]
encb64 = args["encb64"]
org_ident = args["orgident"]
psd_date_time = args["psddatetime"]
psd_names = args["psdnames"]

proxies_fhir = {
    "http": http_proxy_fhir,
    "https": https_proxy_fhir
}

id_doc_ref = str(uuid.uuid4())
id_att = str(uuid.uuid4())

bundle = {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": [],
    "id": id_att
}

psd_names = psd_names.split(",")

def get_existing_doc_ref(project_ident):
    fhir_query = f'{fhir_base_url}/DocumentReference?identifier=http://medizininformatik-initiative.de/sid/project-identifier|{project_ident}'

    if fhir_token is not None:
        resp = requests.get(fhir_query, headers={'Authorization': f"Bearer {fhir_token}"}, proxies=proxies_fhir)
    else:
        resp = requests.get(fhir_query, auth=HTTPBasicAuth(fhir_user, fhir_pw), proxies=proxies_fhir)

    resp_json = resp.json()

    if "entry" in resp_json:
        return resp_json["entry"][0]["resource"]["id"]

    return None


existing_doc_ref_id = get_existing_doc_ref("NT-proBNP")
id_doc_ref = existing_doc_ref_id if existing_doc_ref_id else id_doc_ref

for res_name in psd_names:
    with open(f'pseudonymised_resources/{res_name}_{psd_date_time}.json', 'r') as f:
        cur_resources = json.load(f)

    for resource in cur_resources:
        entry = {
            "fullUrl": f'{resource["resourceType"]}/{resource["id"]}',
            "resource": resource,
            "request": {
                "method": "PUT",
                "url": f'{resource["resourceType"]}/{resource["id"]}'
            }
        }
        bundle['entry'].append(entry)

with open(f'to_send/bundle-to-send_{psd_date_time}.json', 'w') as f:
    json.dump(bundle, f)

datastr = json.dumps(bundle)
b64_encoded_bundle = base64.b64encode(datastr.encode('utf-8'))
with open(f'to_send/b64-encoded-bundle-to-send__{psd_date_time}', 'w') as f:
    f.write(str(b64_encoded_bundle, "utf-8"))

send_bundle = {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": [
        {"fullUrl": f'DocumentReference/{id_doc_ref}',
         "resource": {
            "id": id_doc_ref,
            "resourceType": "DocumentReference",
            "masterIdentifier": {
                "system": "http://medizininformatik-initiative.de/sid/project-identifier",
                "value": "NT-proBNP"
            },
             "status": "current",
             "docStatus": "final",
             "author": {
                "type": "Organization",
                "identifier": {
                    "system": "http://highmed.org/sid/organization-identifier",
                    "value": org_ident
                }
            },
             "date": "2022-09-26T12:15:23.282+00:00",
             "content": {
                "attachment": {
                    "contentType": "application/fhir+json",
                    "url": f'Binary/{id_att}'
                }
            }
         },
         "request": {
             "method": "PUT",
             "url": f'DocumentReference/{id_doc_ref}'
             
         }
         },
        {
            "fullUrl": f'Binary/{id_att}',
            "resource": {
                "id": id_att,
                "resourceType": "Binary",
                "contentType": "text/plain",
                "data": str(b64_encoded_bundle, "utf-8")
            },
            "request": {
                "method": "PUT",
                "url": f'Binary/{id_att}'
            }
        }
    ]
}

if not encb64:

    attachment = {
        "contentType": "application/fhir+json",
        "url": f'Bundle/{id_att}'
    }
    send_bundle["entry"][0]["resource"]["content"]["attachment"] = attachment

    bundle_request = {
        "method": "PUT",
        "url": f'Bundle/{id_att}'
    }
    send_bundle["entry"][1]["fullUrl"] = f'Bundle/{id_att}'
    send_bundle["entry"][1]["resource"] = bundle
    send_bundle["entry"][1]["request"] = bundle_request

with open(f'to_send/fhir-store-bundle__{psd_date_time}.json', 'w') as f:
    json.dump(send_bundle, f)

if send_transaction_bundle:
    if fhir_token is not None:
        resp = requests.post(fhir_base_url, headers={'Authorization': f"Bearer {fhir_token}"},
                             json=send_bundle, proxies=proxies_fhir)
    else:
        resp = requests.post(fhir_base_url, auth=HTTPBasicAuth(
            fhir_user, fhir_pw), json=send_bundle, proxies=proxies_fhir)

    print(resp.json())
