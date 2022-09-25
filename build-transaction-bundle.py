import json
import base64

bundle = {
    "resourceType": "Bundle",
    "type": "transaction",
    "entry": []
}

extracted_res_bundles = ['psd-pats', 'psd-encs', 'psd-obs', 'psd-conds']

for res_name in extracted_res_bundles:
    with open(f'extracted_resources/{res_name}.json', 'r') as f:
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

with open("extracted_resources/bundle-to-send.json", 'w') as f:
    json.dump(bundle, f)

datastr = json.dumps(bundle)
b64_encoded_bundle = base64.b64encode(datastr.encode('utf-8'))
with open("extracted_resources/b64-encoded-bundle-to-send", 'w') as f:
    f.write(str(b64_encoded_bundle, "utf-8"))
