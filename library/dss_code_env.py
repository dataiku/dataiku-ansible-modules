#!/usr/bin/env python2

from __future__ import absolute_import
import six
ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'dataiku-ansible-modules'
}

DOCUMENTATION = '''
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
'''

EXAMPLES = '''
'''

RETURN = '''
dss_code_env:
    description: Return current status of the infra
    type: dict
message:
    description: CREATED, DELETED, MODIFIED or UNCHANGED
    type: str
'''

from ansible.module_utils.basic import AnsibleModule
from dataikuapi import DSSClient
from dataikuapi.dss.admin import DSSCodeEnv
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
    for k, v in six.iteritems(u):
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
        state=dict(type='str', required=False, default="present"),
        name=dict(type='str', required=True),
        lang=dict(type='str', required=True),
        deployment_mode=dict(type='str', required=False, default=None),
        jupyter_support=dict(type='bool', required=False, default=None),
        update=dict(type='bool', required=False, default=True),
        desc=dict(type='dict', required=False, default=None),
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

    if args.lang not in ["PYTHON","R"]:
        module.fail_json(msg="The lang attribute has invalid value '{}'. Must be either 'PYTHON' or 'R'.".format(args.lang))

    result = dict(
        changed=False,
        message='UNCHANGED',
    )

    client = None
    exists = False
    create = False
    code_env = None
    code_env_def = {}
    try:
        client = DSSClient("http://{}:{}".format(args.host, port),api_key=api_key)
        code_envs = client.list_code_envs()

        # Check existence
        for env in code_envs:
            if env["envName"] == args.name and env["envLang"] == args.lang:
                exists=True
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
                if  args.state == "absent":
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
                code_env = client.create_code_env(args.lang,args.name,args.deployment_mode,args.desc)
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
        module.fail_json(msg="{}: {}".format(type(e).__name__,str(e)))

def main():
    run_module()

if __name__ == '__main__':
    main()
