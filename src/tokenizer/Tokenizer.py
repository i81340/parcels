import json
import requests
from common import secrets_manager


def get_credentials():
    return secrets_manager.get_secret('tokenizer_credentials')


credentials = get_credentials()


def process_request(text, is_tokenization_request, is_list):
    url = credentials.get('bulkTokenizerUrl', None)
    if url is not None:
        if is_tokenization_request:
            url = url + "/tokenize/json"
        else:
            url = url + "/detokenize/json"

    if is_list:
        body = text
    else:
        body = {"data": text}

    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.post(url, json.dumps(body), headers=headers)
    response = response.json()
    if is_list:
        return response
    else:
        return response.get('data', None)


def tokenize(text):
    if text:
        return process_request(text, True)
    else:
        return text


def de_tokenize(text):
    return process_request(text, False)


def detokenize_object_list(list, fields_to_tokenize, id_field="id"):
    if list is None:
        return list
    body = {}
    for object in list:
        for field in fields_to_tokenize:
            if object[id_field] and object[field]:
                data = str(object["id"]) + ";" + str(field)
                body[data] = object[field]

    response = process_request(body, False, True)

    for object in list:
        for field in fields_to_tokenize:
            if object[id_field] and object[field]:
                data = str(object["id"]) + ";" + str(field)
                tokenized_value = response.get(data)
                if tokenized_value:
                    object[field] = tokenized_value
