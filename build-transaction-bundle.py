import json
import base64
import uuid
import requests
import argparse
from requests.auth import HTTPBasicAuth

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
parser.add_argument(
    '--storebundle', help='boolean whether to store the bundle in the local fhir server', nargs="?", default=False)


args = vars(parser.parse_args())

fhir_base_url = args["fhirurl"]
fhir_user = args["fhiruser"]
fhir_pw = args["fhirpw"]
fhir_token = args["fhirtoken"]
http_proxy_fhir = args["httpproxyfhir"]
https_proxy_fhir = args["httpsproxyfhir"]
send_transaction_bundle = args["storebundle"]

proxies_fhir = {
    "http": http_proxy_fhir,
    "https": https_proxy_fhir
}

bundle = {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": []
}

psd_date_time = "2022-09-26_10-03-40"
psd_names = ['pats', 'enc', 'obs', 'cond']


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


my_org_ident = "http://test.ukjug.de"
id_doc_ref = str(uuid.uuid4())
id_att = str(uuid.uuid4())

send_bundle = {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": [
        {"fullUrl": id_doc_ref,
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
                    "value": my_org_ident
                }
            },
             "date": "2022-09-26T12:15:23.282+00:00",
             "content": {
                "attachment": {
                    "contentType": "application/json",
                    "url": id_att
                }
            }
         },
         "request": {
             "method": "PUT",
             "url": f'DocumentReference/{id_doc_ref}'
         }
         },
        {
            "fullUrl": id_att,
            "resource": {
                "id": id_att,
                "resourceType": "Binary",
                "contentType": "application/json",
                "data": str(b64_encoded_bundle, "utf-8")
            },
            "request": {
                "method": "PUT",
                "url": f'Binary/{id_att}'
            }
        }
    ]
}

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
