#!/usr/bin/env python

from __future__ import absolute_import

import collections
import copy
import re
import time
import traceback

import ansible.module_utils.dataiku_api_preload_imports
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dataiku_utils import (
    MakeNamespace,
    add_dss_connection_args,
    extract_keys,
    get_client_from_parsed_args,
    update,
)
from ansible.module_utils.dataikuapi.utils import DataikuException

ANSIBLE_METADATA = {"metadata_version": "1.0", "status": ["preview"], "supported_by": "dataiku-ansible-modules"}

DOCUMENTATION = """
---
module: dss_push_container_exec_base_images

short_description: Push the container exec base images to their repository

description:
    - "This module push the container exec base images to their repository"

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
author:
    - Jean-Bernard Jansen (jean-bernard.jansen@dataiku.com)
    - Thibaud Baas (thibaud.baas@dataiku.com)
"""

EXAMPLES = """
- name: Get credentials
  become: true
  become_user: dataiku
  dss_get_credentials:
    datadir: /home/dataiku/dss
    api_key_name: myadminkey
  register: dss_connection_info

- name: Push base images
  become: true
  become_user: dataiku
  dss_push_container_exec_base_images:
    connect_to: "{{ dss_connection_info }}"
"""
RETURN = r''' # '''


def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(settings=dict(type="dict", required=False, default={}),)
    add_dss_connection_args(module_args)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    args = MakeNamespace(module.params)

    result = dict(changed=False)

    client = None
    try:
        client = get_client_from_parsed_args(module)
        general_settings = client.get_general_settings()

        general_settings.push_container_exec_base_images()

        result["changed"] = True

        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg="{}\n\n{}\n\n{}".format(str(e), traceback.format_exc(), "".join(traceback.format_stack())))


def main():
    run_module()


if __name__ == "__main__":
    main()
