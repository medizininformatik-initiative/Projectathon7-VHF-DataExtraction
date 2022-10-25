import json
import argparse
from datetime import datetime
from jsonpath_ng.ext import parse
import uuid
import re
import time
parser = argparse.ArgumentParser()
parser.add_argument(
    '--psddatetime', help='time of pseudonmised resources to use format: 2022-09-26_10-03-40', nargs="?", default=datetime.now().strftime("%Y-%m-%d_%H-%M-%S"))

args = vars(parser.parse_args())
psd_date_time = args["psddatetime"]
psd_site_ident = {
    "use": "usual",
    "type": {
        "coding": [
            {
                "system": "http://mii-randomm-site-identifier",
                "code": "RND-MII-SITE-IDENT"
            }
        ]
    },
    "system": "https://mii-randomm-site-identifier-ident",
    "value": "RND-SITE-IDENT-NUMBER"
}


def obfuscate_date_to_year(field_input):
    return field_input[0:4]


def obfuscate_date_to_day(field_input):
    return field_input[0:10]


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
    id_pool_name = id_change['id_pool']
    if id_pool_name not in id_pseudonyms:
        id_pseudonyms[id_pool_name] = {}

    id_pool = id_pseudonyms[id_pool_name]
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


def change_id_in_obj_by_expression_simple(path, id_change, resource):

    id_pool_name = id_change['id_pool']
    if id_pool_name not in id_pseudonyms:
        id_pseudonyms[id_pool_name] = {}

    id_pool = id_pseudonyms[id_pool_name]
    id_prefix = id_change.get('id_prefix', None)

    if len(path) <= 1:
        cur_key = path.pop(0)
        cur_id = resource[cur_key]
        if id_prefix is not None:
            cur_id = cur_id.replace(id_prefix, "")

        if cur_id not in id_pool:
            psd_id = str(uuid.uuid4())
            id_pool[cur_id] = psd_id
        else:
            psd_id = id_pool[cur_id]

        if id_prefix is not None:
            resource[cur_key] = f'{id_prefix}{psd_id}'
        else:
            resource[cur_key] = psd_id

        return

    cur_key = path.pop(0)
    if "[" in cur_key:
        cur_key = re.sub(r"[\[\]]", "", cur_key)
        cur_key = int(cur_key) if cur_key != "*" else cur_key

    if cur_key == "*":
        for arr_entry in resource:
            change_id_in_obj_by_expression_simple(path, id_change, arr_entry)
    else:

        if cur_key not in resource:
            return

        resource = resource[cur_key]
        change_id_in_obj_by_expression_simple(path, id_change, resource)


def apply_function_to_field_by_expression(to_apply, resource):

    jsonpath_expression = parse(to_apply['path_to_field'])
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

        cur_field = resource[path[len(path) - 1]]

        resource[path[len(path) - 1]
                 ] = globals()[to_apply['function_to_apply']](cur_field)


def apply_function_to_field_by_expression_simple(path, to_apply, resource):

    path = to_apply['path_to_field'].split(".")

    if len(path) <= 1:
        cur_key = path.pop(0)

        if cur_key not in resource:
            return

        cur_field = resource[cur_key]
        resource[cur_key] = globals()[to_apply['function_to_apply']](cur_field)
        return

    cur_key = path.pop(0)
    if "[" in cur_key:
        cur_key = re.sub(r"[\[\]]", "", cur_key)
        cur_key = int(cur_key) if cur_key != "*" else cur_key

    if cur_key == "*":
        for arr_entry in resource:
            apply_function_to_field_by_expression_simple(
                path, to_apply, arr_entry)
    else:
        if cur_key not in resource:
            return
        resource = resource[cur_key]
        apply_function_to_field_by_expression_simple(path, to_apply, resource)


def key_is_array_index(key):
    key = str(key)
    if "[" in key:
        return True

    return False


def select_in_obj_by_expression(selection, psd_resource, resource):

    jsonpath_expression = parse(selection)
    found = jsonpath_expression.find(resource)
    for match in found:
        path = [str(match.path)]
        match = match.context

        while match.context is not None:
            path = [str(match.path)] + path
            match = match.context

        for index in range(0, len(path)):
            cur_key = path[index]
            cur_is_array_key = key_is_array_index(cur_key)
            if cur_is_array_key:
                cur_key = re.sub(r"[\[\]]", "", cur_key)
                cur_key = int(cur_key)

            if index == len(path) - 1:

                if cur_is_array_key:
                    psd_resource.append(resource[cur_key])
                else:
                    psd_resource[cur_key] = resource[cur_key]
                continue

            next_key = path[index + 1]
            if cur_key not in psd_resource:
                if key_is_array_index(next_key):
                    psd_resource[cur_key] = []
                elif cur_is_array_key:
                    psd_resource.append({})
                else:
                    psd_resource[cur_key] = {}

            psd_resource = psd_resource[cur_key]
            resource = resource[cur_key]


def select_in_obj_by_expression_simple(path, psd_resource, resource):

    if not path:
        return

    cur_key = path.pop(0)
    cur_is_array_key = key_is_array_index(cur_key)

    if cur_is_array_key:
        cur_key = re.sub(r"[\[\]]", "", cur_key)

        if cur_key != "*":
            cur_key = int(cur_key)

    if not path:
        if cur_is_array_key:
            psd_resource.append(resource[cur_key])
        elif cur_key in resource:
            psd_resource[cur_key] = resource[cur_key]
        return

    if cur_key == "*":
        psd_res_arr_is_new = True if len(psd_resource) == 0 else False
        for index in range(0, len(resource)):
            arr_entry = resource[index]
            if psd_res_arr_is_new:
                new_arr_entry = {}
                psd_resource.append(new_arr_entry)
            else:
                new_arr_entry = psd_resource[index]
            select_in_obj_by_expression_simple(path, new_arr_entry, arr_entry)
        return

    next_key = path[0]
    if cur_key not in resource:
        return

    if cur_key not in psd_resource:
        if key_is_array_index(next_key):
            psd_resource[cur_key] = []
        elif cur_is_array_key:
            psd_resource.append({})
        else:
            psd_resource[cur_key] = {}

    psd_resource = psd_resource[cur_key]
    resource = resource[cur_key]
    select_in_obj_by_expression_simple(path, psd_resource, resource)

def add_psd_site_ident(psd_resource):

    if 'identifier' not in psd_resource:
        psd_resource['identifier'] = []

    psd_resource['identifier'].append(psd_site_ident)


def pseudonomise_resource(resource, psd_config):

    psd_resource = {}

    for selection in psd_config['select']:
        select_in_obj_by_expression_simple(
            selection.split("."), psd_resource, resource)

    for id_change in psd_config['change_id']:
        change_id_in_obj_by_expression_simple(
            id_change['path_to_id'].split("."), id_change, psd_resource)

    if 'remove' in psd_config:
        for to_remove in psd_config['remove']:
            remove_from_object_by_expression(to_remove, psd_resource)

    if 'apply_function' in psd_config:
        for to_apply in psd_config['apply_function']:
            apply_function_to_field_by_expression_simple(
                to_apply['path_to_field'].split("."), to_apply, psd_resource)

    add_psd_site_ident(psd_resource)

    return psd_resource


def pseudonomise_resources(resource_list, psd_config):
    psd_resources = []
    count = 0
    n_to_pseudonymise = len(resource_list)

    last_time = time.time()
    cur_time = time.time()
    for resource in resource_list:
        psd_resources.append(pseudonomise_resource(resource, psd_config))
        count = count + 1
        if count % 100 == 0:
            print(
                f'N resources pseudonymised: {str(count)}/{str(n_to_pseudonymise)}')
            cur_time = time.time()
            time_taken_100 = cur_time - last_time
            print(f'time taken for 100 res = {time_taken_100}')
            last_time = cur_time

    return psd_resources


id_pseudonyms = {}
psd_site_ident['value'] = str(uuid.uuid4())
id_pseudonyms['site_id_pseudonym'] = psd_site_ident['value']

with open("psd_config.json", 'r') as f:
    psd_configs = json.load(f)

for psd_config in psd_configs:
    input_file = f'{psd_config["input_file_path"]}/{psd_config["psd_name"]}.json'

    with open(input_file, 'r') as f:
        input_list = json.load(f)

    print(f'Begin pseudonymisation of: {input_file}...')
    psd_list = pseudonomise_resources(input_list, psd_config)
    print(f'Finished pseudonymisation of: {input_file}')
    output_file = f'{psd_config["psd_file_path"]}/{psd_config["psd_name"]}_{psd_date_time}.json'
    with open(output_file, 'w') as f:
        json.dump(psd_list, f)

id_psd_file = f'{psd_config["psd_file_path"]}/id_pseudonyms_{psd_date_time}_.json'
with open(id_psd_file, 'w') as f:
    json.dump(id_pseudonyms, f)
