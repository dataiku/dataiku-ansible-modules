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

ANSIBLE_METADATA = {"metadata_version": "1.1", "status": ["preview"], "supported_by": "dataiku-ansible-modules"}

DOCUMENTATION = """
---
module: dss_code_env

short_description: Read the conf of a code env or setup a new one

description:

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
    lang:
        description:
            - The API Key to authenticate on the API. Mandatory if connect_to is not used. Required to create it.
        required: false
    name:
        description;
            - Name of the code env
        required: true
    deployment_mode:
        description:
            - The deployment mode
        required: true
    jupyter_support:
        description:
            - Enable jupyter support for this code env
        required: false
    desc:
        description:
            - Additional configuration of the code env. Depends on its type, see documentation
        required: false
    update:
        description:
            - Update packages to match spec if the code env def changed. Default true.
        required: false
    state:
        description:
            - Is the code env supposed to be there or not. Either "present" or "absent". Default "present"
        required: false
author:
    - Jean-Bernard Jansen (jean-bernard.jansen@dataiku.com)
"""

EXAMPLES = """
"""

RETURN = """
dss_code_env:
    description: Return current status of the infra
    type: dict
message:
    description: CREATED, DELETED, MODIFIED or UNCHANGED
    type: str
"""



def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        state=dict(type="str", required=False, default="present"),
        name=dict(type="str", required=True),
        lang=dict(type="str", required=True),
        deployment_mode=dict(type="str", required=False, default=None),
        jupyter_support=dict(type="bool", required=False, default=None),
        update=dict(type="bool", required=False, default=True),
        desc=dict(type="dict", required=False, default=None),
    )
    add_dss_connection_args(module_args)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    args = MakeNamespace(module.params)

    if args.lang not in ["PYTHON", "R"]:
        module.fail_json(
            msg="The lang attribute has invalid value '{}'. Must be either 'PYTHON' or 'R'.".format(args.lang)
        )

    result = dict(changed=False, message="UNCHANGED",)

    client = None
    exists = False
    create = False
    code_env = None
    code_env_def = {}
    try:
        client = get_client_from_parsed_args(module)
        code_envs = client.list_code_envs()

        # Check existence
        for env in code_envs:
            if env["envName"] == args.name and env["envLang"] == args.lang:
                exists = True
                break

        if not exists and args.state == "present":
            create = True

        if exists:
            code_env = client.get_code_env(args.lang, args.name)
            code_env_def = code_env.get_definition()

        # Prepare the result for dry-run mode
        result["changed"] = create or (exists and args.state == "absent")
        if result["changed"]:
            if create:
                result["message"] = "CREATED"
            elif exists:
                if args.state == "absent":
                    result["message"] = "DELETED"
                else:
                    result["message"] = "UNMODIFIED"

        if module.check_mode:
            module.exit_json(**result)

        # Apply the changes
        if args.state == "present":
            previous_code_env_def = copy.deepcopy(code_env_def)
            if create:
                if args.deployment_mode is None:
                    raise Exception("The argument deployment_mode is mandatory to create a code env")
                code_env = client.create_code_env(args.lang, args.name, args.deployment_mode, args.desc)
                code_env_def = code_env.get_definition()

            if args.desc is not None:
                update(code_env_def, args.desc)

            if args.jupyter_support is not None:
                code_env.set_jupyter_support(args.jupyter_support)

            code_env_def = code_env.get_definition()
            result["dss_code_env"] = code_env_def

            if previous_code_env_def != code_env_def:
                if args.update and not create:
                    code_env.update_packages()
                result["changed"] = True
                result["message"] = "MODIFIED"

        if args.state == "absent" and exits:
            if exists:
                code_env.delete()
                result["message"] = "DELETED"

        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg="{}\n\n{}\n\n{}".format(str(e), traceback.format_exc(), "".join(traceback.format_stack())))


def main():
    run_module()


if __name__ == "__main__":
    main()
