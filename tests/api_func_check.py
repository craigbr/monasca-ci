# Copyright 2015 Hewlett-Packard
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import datetime
import json
import random
import requests
import sys
import time
import urllib
import yaml

from jsonschema import validate

from monascaclient import ksclient

timestamp_pattern = ("[0-9]{2}-[0-9]{2}-[0-9]{2}T" +
                     "[0-9]{2}:[0-9]{2}:[0-9]{2}(.[0-9]{0,3})?Z")

list_schema = {
    "type": "object",
    "properties": {
        "links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rel": {"type": "string"},
                    "href": {"type": "string"}
                },
                "required": ["rel", "href"]
            },
        },
        "elements": {
            "type": "array",
            # "items": None
        }
    },
    "required": ["links", "elements"]
}

version_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rel": {"type": "string"},
                    "href": {"type": "string"}
                },
                "required": ["rel", "href"]}
        },
        "status": {"type": "string"},
        "updated": {"updated": "string",
                    "pattern": timestamp_pattern}
    }
}

metric_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "dimensions": {"type": "object"}
    },
    "required": ["id", "name"]
}

metric_name_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"}
    },
    "required": ["name"]
}

measurement_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "dimensions": {"type": "object"},
        "columns": {
            "type": "array",
            "items": {"type": "string"}
        },
        "measurements": {
            "type": "array",
            "items": {"type": "array"}
        }
    },
    "required": ["id", "name", "measurements"]
}

statistics_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "dimensions": {"type": "object"},
        "columns": {
            "type": "array",
            "items": {"type": "string"}
        },
        "statistics": {
            "type": "array",
            "items": {"type": "array"}
        }
    },
    "required": ["name", "columns", "statistics"]
}

notification_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rel": {"type": "string"},
                    "href": {"type": "string"}},
                "required": ["rel", "href"]}},
        "name": {"type": "string"},
        "type": {
            "type": "string",
            "enum": ["WEBHOOK", "EMAIL", "PAGERDUTY"]},
        "address": {"type": "string"}}
}

alarm_definition_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rel": {"type": "string"},
                    "href": {"type": "string"}},
                "required": ["rel", "href"]}},
        "name": {"type": "string"},
        "description": {"type": ["string", "null"]},
        "expression": {"type": "string"},
        "match_by": {
            "type": "array",
            "items": {"type": "string"}},
        "severity": {"type": "string"},
        "ok_actions": {
            "type": ["array", "null"],
            "items": {"type": "string"}},
        "alarm_actions": {
            "type": ["array", "null"],
            "items": {"type": "string"}},
        "undetermined_actions": {
            "type": ["array", "null"],
            "items": {"type": "string"}}},
    "required": ["id", "links", "name", "description", "expression",
                 "match_by","severity", "ok_actions", "alarm_actions",
                 "undetermined_actions"]
}

alarm_history_schema = {
    "type": "object",
    "properties": {
        "id": {"type": ["number", "string"]},
        "alarm_id": {"type": "string"},
        "metrics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": ["string", "null"]},
                    "name": {"type": "string"},
                    "dimensions": {"type": "object"}}}},
        "old_state": {"type": "string",
                      "enum": ["OK", "ALARM", "UNDETERMINED"]},
        "new_state": {"type": "string",
                      "enum": ["OK", "ALARM", "UNDETERMINED"]},
        "reason": {"type": "string"},
        "reason_data": {"type": "string"},
        "timestamp": {"type": "string",
                      "pattern": timestamp_pattern},
        "sub_alarms": {
            "type": ["array", "null"],
            "items": {
                "type": "object",
                "properties": {
                    "sub_alarm_expression": {
                        "type": "object",
                        "properties": {
                            "function": {"type": "string"},
                            "metric_name": {"type": "string"},
                            "dimensions": {"type": "object"},
                            "operator": {"type": "string"},
                            "threshold": {"type": "number"},
                            "period": {"type": "number"},
                            "periods": {"type": "number"}},
                        "required": ["function", "metric_name", "dimensions",
                                     "operator", "threshold", "period",
                                     "periods"]},
                    "sub_alarm_state": {"type": "string",
                                        "enum": ["OK", "ALARM",
                                                 "UNDETERMINED"]},
                    "current_values": {
                        "type": ["array", "null"],
                        "items": {"type": "number"}}}}}}
}

alarm_schema = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "links": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rel": {"type": "string"},
                    "href": {"type": "string"}
                },
                "required": ["rel", "href"]}
        },
        "alarm_definition": {
            "type": "object",
            "properties": {
                "severity": {"type": "string"},
                "id": {"type": "string"},
                "links": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rel": {"type": "string"},
                            "href": {"type": "string"}
                        },
                        "required": ["rel", "href"]}
                },
                "name": {"type": "string"}},
            "required": ["severity", "id", "links", "name"]
        },
        "metrics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "dimensions": {"type": "object"}
                },
                "required": ["name"]
            }
        },
        "state": {"type": "string",
                  "enum": ["OK", "ALARM", "UNDETERMINED"]},
        "lifecycle_state": {"type": ["string", "null"]},
        "link": {"type": ["string", "null"]},
        "state_updated_timestamp": {"type": "string",
                                    "pattern": timestamp_pattern},
        "updated_timestamp": {"type": "string",
                              "pattern": timestamp_pattern},
        "created_timestamp": {"type": "string",
                              "pattern": timestamp_pattern}
    },
    "required": ["id", "links", "alarm_definition", "metrics", "state",
                 "lifecycle_state", "link", "state_updated_timestamp",
                 "updated_timestamp", "created_timestamp"]
}


class APIConnection(object):
    def __init__(self, api_url, keystone_config):
        self.url = api_url
        if api_url[-1] == '/':
            self.base_url, self.version = api_url[:-1].rsplit('/', 1)
        else:
            self.base_url, self.version = api_url.rsplit('/', 1)

        self.ks = ksclient.KSClient(**keystone_config)
        self.headers = {'X-Auth-User': keystone_config['username'],
                        'X-Auth-Token': self.ks.token,
                        'X-Auth-Key': keystone_config['password'],
                        'Accept': 'application/json',
                        'User-Agent': 'python-monascaclient',
                        'Content-Type': 'application/json'}

    def do_request(self, method, rel_url='', body=None):
        return requests.request(method=method,
                                url=self.url+rel_url,
                                data=json.dumps(body),
                                headers=self.headers)


def verify_response_code(res, expected):
    message = "Invalid response code {}, expected {}\n{}"
    assert res.status_code == expected, message.format(res.status_code,
                                                       expected,
                                                       res.text)


# test version info
def test_version_list(api):
    response = requests.request(method="GET",
                                url=api.base_url,
                                headers=api.headers)

    verify_response_code(response, 200)
    json_data = json.loads(response.text)

    list_schema['properties']['elements']['items'] = version_schema
    validate(json_data, list_schema)
    version_list = []
    for element in json_data['elements']:
        version_list.append(element['id'])

    assert api.version in version_list, "Version '{}' not found".format(api.version)


def test_version_get(api):
    response = api.do_request("GET")

    verify_response_code(response, 200)
    json_data = json.loads(response.text)
    validate(json_data, version_schema)

    message = "Version '{}' did not match requested version '{}'"
    assert json_data['id'] == api.version, message.format(json_data['id'], api.version)


# test metric post and list
def test_metric_post(api):
    body = {
        "name": "name1",
        "dimensions": {
            "key1": "value1",
            "key2": "value2"
        },
        "timestamp": time.time()*1000,
        "value": 1.0
    }

    response = api.do_request("POST", "/metrics", body)

    verify_response_code(response, 204)


def test_metric_post_value_meta(api):
    body = {
        "name": "name1",
        "dimensions": {
            "key1": "value1",
            "key2": "value2"},
        "timestamp": time.time()*1000,
        "value": 1.0,
        "value_meta": {
            "key1": "value1",
            "key2": "value2"
        }
    }

    response = api.do_request("POST", "/metrics", body)

    verify_response_code(response, 204)


def test_metric_post_array(api):
    body = [
        {
            "name": "name1",
            "dimensions": {
                "key1": "value1",
                "key2": "value2"},
            "timestamp": time.time()*1000,
            "value": 1.0},
        {
            "name": "name2",
            "dimensions": {
                "key1": "value1",
                "key2": "value2"},
            "timestamp": time.time()*1000,
            "value": 2.0,
            "value_meta": {
                "key1": "value1",
                "key2": "value2"}}]

    response = api.do_request("POST", "/metrics", body)

    verify_response_code(response, 204)


def test_metric_list(api):
    response = api.do_request("GET", "/metrics")

    verify_response_code(response, 200)

    json_data = json.loads(response.text)
    list_schema['properties']['elements']['items'] = metric_schema
    validate(json_data, list_schema)


def test_metric_name_list(api):
    response = api.do_request("GET", "/metrics/names")

    verify_response_code(response, 200)

    json_data = json.loads(response.text)
    list_schema['properties']['elements']['items'] = metric_name_schema
    validate(json_data, list_schema)


def test_measurement_list(api):
    one_hour_ago = datetime.datetime.utcnow()-datetime.timedelta(hours=1)
    one_hour_ago = one_hour_ago - datetime.timedelta(microseconds=
                                                     one_hour_ago.microsecond)

    query_params = {
        "name": "name1",
        "start_time": one_hour_ago.isoformat()+'Z',
    }
    query_str = urllib.urlencode(query_params)

    response = api.do_request("GET", "/metrics/measurements?"+query_str)

    verify_response_code(response, 200)

    json_data = json.loads(response.text)
    list_schema['properties']['elements']['items'] = measurement_schema
    validate(json_data, list_schema)


def test_statistics_get(api):
    one_hour_ago = datetime.datetime.utcnow()-datetime.timedelta(minutes=1)
    one_hour_ago = one_hour_ago - datetime.timedelta(microseconds=
                                                     one_hour_ago.microsecond)

    query_params = {
        "name": "name1",
        "start_time": one_hour_ago.isoformat()+'Z',
        "statistics": "count,max,min,avg"
    }
    query_str = urllib.urlencode(query_params)

    response = api.do_request("GET", "/metrics/statistics?"+query_str)

    verify_response_code(response, 200)

    json_data = json.loads(response.text)
    list_schema['properties']['elements']['items'] = statistics_schema
    validate(json_data, list_schema)


def test_notification_CRUD(api):
    # define a random name to reduce chances of collision
    notif_name = "Test_api_func_{}".format(random.randint(1, 1000000))

    body = {
        "name": notif_name,
        "type": "WEBHOOK",
        "address": "http://somesite.com"
    }

    response = api.do_request("POST", "/notification-methods", body)

    verify_response_code(response, 201)

    json_data = json.loads(response.text)
    validate(json_data, notification_schema)
    message = "Name was {}, expected {}"
    assert json_data['name'] == body['name'], message.format(json_data['name'],
                                                             body['name'])

    notification_id = json_data['id']

    response = api.do_request("GET", "/notification-methods")

    verify_response_code(response, 200)

    json_data = json.loads(response.text)
    list_schema['properties']['elements']['items'] = notification_schema
    validate(json_data, list_schema)

    response = api.do_request("GET", "/notification-methods/"+notification_id)

    verify_response_code(response, 200)

    json_data = json.loads(response.text)
    validate(json_data, notification_schema)
    assert json_data['id'] == notification_id

    body = {
        "name": notif_name,
        "type": "EMAIL",
        "address": "someone@somewhere.com"
    }

    response = api.do_request("PUT", "/notification-methods/"+notification_id,
                          body)

    verify_response_code(response, 200)

    json_data = json.loads(response.text)
    validate(json_data, notification_schema)
    message = "Type was {}, expected {}"
    assert json_data['type'] == body['type'], message.format(json_data['type'],
                                                             body['type'])

    response = api.do_request("DELETE", "/notification-methods/"+notification_id)

    verify_response_code(response, 204)


# test alarm definitions
def test_alarm_definition_CRUD(api):
    # define a random name to reduce chances of collision
    def_name = "Test_api_func_{}".format(random.randint(1, 1000000))

    # create
    body = {
        "name": def_name,
        "expression": "test_api_function > 0",
        "match_by": [
            "test-dim"
        ]
    }

    response = api.do_request("POST", "/alarm-definitions", body)

    verify_response_code(response, 201)
    json_data = json.loads(response.text)
    validate(json_data, alarm_definition_schema)
    definition_id = json_data['id']

    response = api.do_request("GET", "/alarm-definitions")

    verify_response_code(response, 200)
    json_data = json.loads(response.text)

    list_schema['properties']['elements']['items'] = alarm_definition_schema
    validate(json_data, list_schema)

    # list
    response = api.do_request("GET", "/alarm-definitions/"+definition_id)

    verify_response_code(response, 200)
    json_data = json.loads(response.text)
    validate(json_data, alarm_definition_schema)

    # update
    body = {
        "name": def_name,
        "expression": "test_api_function > 0",
        "match_by": [
            "test-dim"
        ],
        "actions_enabled": True
    }

    response = api.do_request("PUT", "/alarm-definitions/"+definition_id, body)

    verify_response_code(response, 200)
    json_data = json.loads(response.text)
    validate(json_data, alarm_definition_schema)

    # patch
    body = {
        "name": def_name,
        "severity": "HIGH"
    }

    response = api.do_request("PATCH", "/alarm-definitions/"+definition_id, body)

    verify_response_code(response, 200)
    json_data = json.loads(response.text)
    validate(json_data, alarm_definition_schema)

    # delete
    response = api.do_request("DELETE", "/alarm-definitions/"+definition_id)

    verify_response_code(response, 204)


def test_alarm_state_history_list(api):
    response = api.do_request("GET", "/alarms/state-history")

    verify_response_code(response, 200)

    json_data = json.loads(response.text)
    list_schema['properties']['elements']['items'] = alarm_history_schema
    validate(json_data, list_schema)


def test_alarm_list_get_update_delete(api):
    # alarm list
    response = api.do_request("GET", "/alarms")

    verify_response_code(response, 200)
    json_data = json.loads(response.text)

    list_schema['properties']['elements']['items'] = alarm_schema
    validate(json_data, list_schema)
    alarm_id = json_data['elements'][0]['id']

    # alarm update
    body = {
        "state": "ALARM",
        "lifecycle_state": "open",
        "link": "http://somesite.com"
    }

    response = api.do_request("PUT", "/alarms/"+alarm_id, body)

    verify_response_code(response, 200)

    response = api.do_request("GET", "/alarms/"+alarm_id)

    verify_response_code(response, 200)
    json_data = json.loads(response.text)
    validate(json_data, alarm_schema)
    assert json_data['state'] == "ALARM"
    assert json_data['lifecycle_state'] == "open"
    assert json_data['link'] == "http://somesite.com"

    # alarm patch
    body = {
        "state": "OK",
        "lifecycle_state": "closed"
    }

    response = api.do_request("PATCH", "/alarms/"+alarm_id, body)

    verify_response_code(response, 200)
    json_data = json.loads(response.text)
    validate(json_data, alarm_schema)
    assert json_data['lifecycle_state'] == "closed"

    response = api.do_request("GET", "/alarms/"+alarm_id)

    verify_response_code(response, 200)
    json_data = json.loads(response.text)
    validate(json_data, alarm_schema)
    assert json_data['lifecycle_state'] == "closed"
    assert json_data['link'] == "http://somesite.com"

    # alarm delete
    response = api.do_request("DELETE", "/alarms/"+alarm_id)

    verify_response_code(response, 204)

    response = api.do_request("GET", "/alarms/"+alarm_id)

    verify_response_code(response, 404)


def main(argv=None):
    if argv is None:
        argv = sys.argv
    if len(argv) != 2:
        print "Usage: " + argv[0] + " <config yaml>"
        return 1

    with open(argv[1], 'r') as config_yaml:
        config = yaml.load(config_yaml.read())

    api = APIConnection(config['monasca_api_url'], config['keystone'])

    test_version_list(api)
    test_version_get(api)

    test_notification_CRUD(api)

    test_metric_post(api)
    test_metric_post_array(api)
    test_metric_post_value_meta(api)
    test_metric_list(api)
    test_metric_name_list(api)
    test_measurement_list(api)
    test_statistics_get(api)

    test_alarm_definition_CRUD(api)

    test_alarm_state_history_list(api)
    test_alarm_list_get_update_delete(api)

    print("pass")


if __name__ == "__main__":
    main()
