#!/usr/bin/env python

from __future__ import absolute_import
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
            - General settings values to modify. Can be ignored to just get the current values
        required: false
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

- name: Setup LDAP connectivity
  become: true
  become_user: dataiku
  dss_general_settings:
    connect_to: "{{dss_connection_info}}"
    settings:
      ldapSettings:
        enabled: true
        url: ldap://ldap.internal.example.com/dc=example,dc=com
        bindDN: uid=readonly,ou=users,dc=example,dc=com
        bindPassword: theserviceaccountpassword
        useTls: true
        autoImportUsers: true
        userFilter: (&(objectClass=posixAccount)(uid={USERNAME}))
        defaultUserProfile: READER
        displayNameAttribute: gecos
        emailAttribute: mail
        enableGroups: true
        groupFilter: (&(objectClass=posixGroup)(memberUid={USERDN}))
        groupNameAttribute: cn
        groupProfiles: []
        authorizedGroups: dss-users
'''

RETURN = '''
previous_settings:
    description: Previous values held by required settings before update
    type: dict
dss_general_settings:
    description: Return the current values after update
    type: dict
message:
    description: MODIFIED or UNCHANGED
    type: str
'''

from ansible.module_utils.basic import AnsibleModule
import ansible.module_utils.dataiku_api_preload_imports
from ansible.module_utils.dataikuapi.utils import DataikuException
from ansible.module_utils.dataiku_utils import MakeNamespace, add_dss_connection_args, get_client_from_parsed_args, update, extract_keys

import copy
import traceback
import re
import time
import collections

def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        settings=dict(type='dict', required=False, default={}),
    )
    add_dss_connection_args(module_args)

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    args = MakeNamespace(module.params)

    result = dict(
        changed=False,
        message='UNCHANGED',
        previous_settings=None,
        settings=None
    )

    client = None
    general_settings = None
    try:
        client = get_client_from_parsed_args(module)
        general_settings = client.get_general_settings()
        current_values = extract_keys(general_settings.settings, args.settings)

        # Prepare the result for dry-run mode
        result["previous_settings"] = current_values
        result["dss_general_settings"] = general_settings.settings
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
        module.fail_json(msg="{}\n\n{}\n\n{}".format(str(e),traceback.format_exc(),"".join(traceback.format_stack())))

def main():
    run_module()

if __name__ == '__main__':
    main()
