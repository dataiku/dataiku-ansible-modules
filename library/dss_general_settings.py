#!/usr/bin/env python2

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'dataiku-ansible-modules'
}

DOCUMENTATION = '''
---
module: dss_general_settings

short_description: Set up general settings values

description:
    - "This module edits DSS general settings"

options:
    connect_to:
        description:
            - A dictionary containing "port" and "api_key". This parameter is a short hand to be used with dss_get_credentials
        required: true
    host:
        description:
            - The host on which to make the requests.
        required: false
        default: localhost
    port:
        description:
            - The port on which to make the requests. Mandatory if connect_to is not used
        required: false
        default: 80
    api_key:
        description:
            - The API Key to authenticate on the API. Mandatory if connect_to is not used
        required: false
    settings:
        description:
            - General settings values to modify
        required: true
author:
    - Jean-Bernard Jansen (jean-bernard.jansen@dataiku.com)
'''

EXAMPLES = '''
- name: Get credentials
  become: true
  become_user: dataiku
  dss_get_credentials:
    datadir: /home/dataiku/dss
    api_key_name: myadminkey
  register: dss_connection_info

- name: Setup some limits
  become: true
  become_user: dataiku
  dss_general_settings:
    connect_to: "{{dss_connection_info}}"
    settings:
      limits:
        attachmentBytes:
          hard: -1
          soft: -1
        memSampleBytes:
          hard: 524288000
          soft: 104857600
        shakerMemTableBytes:
          hard: 524288000
          soft: -1
'''

RETURN = '''
previous_settings:
    description: The previous values
    type: dict
settings:
    description: The current values
    type: dict
message:
    description: MODIFIED or UNCHANGED
    type: str
'''

from ansible.module_utils.basic import AnsibleModule
from dataikuapi import DSSClient
from dataikuapi.dss.admin import DSSGeneralSettings
from dataikuapi.utils import DataikuException
import copy
import traceback
import re
import time
import collections

# Trick to expose dictionary as python args
class MakeNamespace(object):
    def __init__(self,values):
        self.__dict__.update(values)

# Similar to dict.update but deep
def update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, collections.Mapping):
            d[k] = update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

def extract_keys(input_data, keys_reference):
    extracted_data = {}
    for k, v in keys_reference.items():
        if isinstance(v, collections.Mapping):
            extracted_data[k] = extract_keys(input_data[k],v)
        else:
            extracted_data[k] = input_data.get(k,None) 
    return extracted_data


def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        connect_to=dict(type='dict', required=False, default={}, no_log=True),
        host=dict(type='str', required=False, default="127.0.0.1"),
        port=dict(type='str', required=False, default=None),
        api_key=dict(type='str', required=False, default=None),
        settings=dict(type='dict', required=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    args = MakeNamespace(module.params)
    api_key = args.api_key if args.api_key is not None else args.connect_to.get("api_key",None)
    if api_key is None:
        module.fail_json(msg="Missing an API Key, either from 'api_key' or 'connect_to' parameters".format(args.state))
    port = args.port if args.port is not None else args.connect_to.get("port","80")
    host = args.host

    result = dict(
        changed=False,
        message='UNCHANGED',
        previous_settings=None,
        settings=None
    )

    client = None
    general_settings = None
    try:
        client = DSSClient("http://{}:{}".format(args.host, port),api_key=api_key)
        general_settings = client.get_general_settings()
        current_values = extract_keys(general_settings.settings, args.settings)

        # Prepare the result for dry-run mode
        result["previous_settings"] = current_values
        result["settings"] = args.settings
        result["changed"] = (current_values != args.settings)
        if result["changed"]:
            result["message"] = "MODIFIED"

        if module.check_mode:
            module.exit_json(**result)

        # Apply the changes
        update(general_settings.settings, args.settings)
        general_settings.save()
        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg="{}: {}".format(type(e).__name__,str(e)))

def main():
    run_module()

if __name__ == '__main__':
    main()
