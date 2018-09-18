#!/usr/bin/env python2

ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'dataiku-ansible-modules'
}

DOCUMENTATION = '''
---
module: dss_api_deployer_infra

short_description: Set up an API Deployer infrastructure

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
author:
    - Jean-Bernard Jansen (jean-bernard.jansen@dataiku.com)
'''

EXAMPLES = '''
- name: Get API credentials
  become: true
  become_user: dataiku
  dss_get_credentials:
    datadir: /home/dataiku/api
    api_key_name: myadminkey
  register: dss_api_info

- name: Get credentials
  become: true
  become_user: dataiku
  dss_get_credentials:
    datadir: /home/dataiku/dss
    api_key_name: myadminkey
  register: dss_connection_info

- name: Setup an infra
  become: true
  become_user: dataiku
  dss_api_deployer_infra:
    connect_to: "{{dss_connection_info}}"
    id: infra_dev
    type: STATIC
    stage: Development
    api_nodes:
      - url: "http://localhost:{{dss_api_info.port}}/"
        admin_api_key: "{{dss_api_info.api_key}}"
        graphite_prefix: apinode
    permissions:
      - group: "data_team"
        read: true
        deploy: true
        admin: false
'''

RETURN = '''
dss_api_deployer_infra:
    description: Return current status of the infra
    type: dict
message:
    description: CREATED, DELETED, MODIFIED or UNCHANGED
    type: str
'''

from ansible.module_utils.basic import AnsibleModule
from dataikuapi import DSSClient
from dataikuapi.dss.admin import DSSGeneralSettings
from dataikuapi.dss.apideployer import DSSAPIDeployer, DSSAPIDeployerInfra, DSSAPIDeployerInfraSettings
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
        state=dict(type='str', required=False, default="present"),
        id=dict(type='str', required=True),
        stage=dict(type='str', required=True),
        type=dict(type='str', required=True),
        api_nodes=dict(type='list', required=True),
        permissions=dict(type='list',required=False,default=[]),
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
        id=args.id,
    )

    client = None
    exists = True
    create = False
    infra = None
    try:
        client = DSSClient("http://{}:{}".format(args.host, port),api_key=api_key)
        api_deployer = client.get_apideployer()
        infras_status = api_deployer.list_infras(as_objects=False)
        infras_id = []
        for infra_status in infras_status:
            infras_id.append(infra_status["infraBasicInfo"]["id"])
        exists = args.id in infras_id
        if not exists and args.state == "present":
            create = True

        result["changed"] = create or (exists and args.state == "absent")
        if result["changed"]:
            if create:
                result["message"] = "CREATED"
            elif exists:
                if  args.state == "absent":
                    result["message"] = "DELETED"
                elif current != new_def:
                    result["message"] = "MODIFIED"

        # Prepare the result for dry-run mode
        if module.check_mode:
            module.exit_json(**result)

        # Apply the changes
        if args.state == "present":
            if create:
                infra = api_deployer.create_infra(args.id, args.stage, args.type)
            else:
                infra = api_deployer.get_infra(args.id)
            infra_settings = infra.get_settings()
            previous_settings = copy.deepcopy(infra_settings.get_raw())

            # Remove all / push all
            infra_settings.get_raw()["permissions"] = args.permissions
            infra_settings.get_raw()["apiNodes"] = []
            for api_node in args.api_nodes:
                infra_settings.add_apinode(api_node["url"], api_node["admin_api_key"], api_node.get("graphite_prefix",None))
            infra_settings.save()
            if infra_settings.get_raw() != previous_settings and not result["changed"]:
                result["changed"] = True
                result["message"] = "MODIFIED"

        if args.state == "absent" and exits:
            # TODO implement
            pass
            
        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg="{}: {}".format(type(e).__name__,str(e)))

def main():
    run_module()

if __name__ == '__main__':
    main()
