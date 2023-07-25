import json
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--inputfilepath', help='path to file which should be cleaned',
                    default="to_send/bundle-to-send_2023-07-11_12-05-43.json")

args = vars(parser.parse_args())
input_file = args["inputfilepath"].replace(".json", "")

input_resources = {}
supported_types = ['Patient', "Encounter", "Condition", "Observation"]

id_pseudonyms = {
    "Patient": {},
    "Encounter": {},
    "Condition": {},
    "Observation": {}
}

with open(f'{input_file}.json', 'r') as f:
    input_resources = json.load(f)


for entry in input_resources['entry']:
    cur_res = entry['resource']
    cur_type = cur_res['resourceType']

    if cur_res['id'] in id_pseudonyms[cur_type]:
        print(f'Duplicate main Id {cur_res["id"]} of resource  - Error in data => exiting')
        exit()

    id_pseudonyms[cur_type][cur_res['id']] = True

for entry in input_resources['entry']:
    cur_res = entry['resource']
    cur_type = cur_res['resourceType']

    if "Observation" == cur_type:

        if cur_res["subject"]["reference"].replace("Patient/", "") not in id_pseudonyms["Patient"]:
            print(
                f'Referenced Patient for resource {cur_res} not found - Error in data  => exiting')
            exit()

        if "encounter" in cur_res:
            if cur_res["encounter"]["reference"].replace("Encounter/", "") not in id_pseudonyms["Encounter"]:
                print(
                    f'Encounter for Observation {cur_res["id"]} not found - deleting Reference')
                del cur_res["encounter"]

    if "Encounter" == cur_type:
        indices_to_delete = []

        if cur_res["subject"]["reference"].replace("Patient/", "") not in id_pseudonyms["Patient"]:
            print(
                f'Referenced Patient for resource {cur_res} not found - Error in data  => exiting')
            exit()

        if "diagnosis" in cur_res:
            for index in range(0, len(cur_res["diagnosis"])):
                if "reference" not in cur_res["diagnosis"][index]['condition']:
                    continue

                if cur_res["diagnosis"][index]['condition']['reference'].replace("Condition/", "") not in id_pseudonyms["Condition"]:
                    indices_to_delete.append(index)

            for index in sorted(indices_to_delete, reverse=True):
                print(
                    f'Encounter: Diagnosis {cur_res["diagnosis"][index]} not found -> deleting reference')
                del cur_res["diagnosis"][index]

    if "Condition" == cur_type:
        if cur_res["subject"]["reference"].replace("Patient/", "") not in id_pseudonyms["Patient"]:
            print(
                f'Referenced Patient for resource {cur_res} not found - Error in data  => exiting')
            exit()

        if "encounter" in cur_res:
            if cur_res["encounter"]["reference"].replace("Encounter/", "") not in id_pseudonyms["Encounter"]:
                print(
                    f'Condition: Encounter for Condition {cur_res["id"]} not found - deleting Encounter Reference')
                del cur_res["encounter"]


cleaned_ref_file = f'{input_file}_cleaned.json'
with open(cleaned_ref_file, 'w') as f:
    json.dump(input_resources, f)
