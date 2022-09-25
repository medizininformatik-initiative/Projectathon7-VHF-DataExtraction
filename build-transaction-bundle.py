import json

obs_id_pseudonyms = {}
pat_id_pseudonyms = {}
enc_id_pseudonyms = {}
cond_id_pseudonyms = {}


with open('extracted_resources/psd-obs-ids.json', 'r') as f:
    obs_id_pseudonyms = json.load(f)

with open('extracted_resources/psd-pat-ids.json', 'r') as f:
    pat_id_pseudonyms = json.load(f)

with open('extracted_resources/psd-enc-ids.json', 'r') as f:
    enc_id_pseudonyms = json.load(f)

with open('extracted_resources/psd-cond-ids.json', 'r') as f:
    cond_id_pseudonyms = json.load(f)


