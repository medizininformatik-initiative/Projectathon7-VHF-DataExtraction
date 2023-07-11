import json

input_file = "to_send/bundle-to-send_2023-06-30_07-52-10.json"
input_resources = {}

output_resources = {}

supported_types = ['Patient', "Encounter", "Condition", "Observation"]

type_to_abbr = {
    "Patient": "pats",
    "Encounter": "enc",
    "Condition": "cond",
    "Observation": "obs"
}

for type in supported_types:
    output_resources[type] = []

with open(input_file, 'r') as f:
    input_resources = json.load(f)


for entry in input_resources['entry']:
  
    cur_res = entry['resource']
    cur_type = cur_res['resourceType']

    output_resources[cur_type].append(cur_res)


for type in supported_types:
    to_write = output_resources[type]

    output_file = f'extracted_resources_h_bundle/{type_to_abbr[type]}.json'
    with open(output_file, 'w+') as f:
        json.dump(to_write, f)
