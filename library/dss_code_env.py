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
               DESIGN_MANAGED, DESIGN_NON_MANAGED, PLUGIN_MANAGED, PLUGIN_NON_MANAGED, AUTOMATION_VERSIONED, AUTOMATION_SINGLE, AUTOMATION_NON_MANAGED_PATH, EXTERNAL_CONDA_NAMED
        required: true
    version:
        description:
            - The version to affect when used with automation node
        required: true
    core_packages:
        description:
            - Installs the core packages required tu use Dataiku API
        required: false
    jupyter_support:
        description:
            - Enable jupyter support for this code env
        required: false
    permissions:
        required: False
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
---
- name: Get the API Key
  become: true
  become_user: dataiku
  dss_get_credentials:
    datadir: /home/dataiku/dss
    api_key_name: myadminkey
  register: dss_connection_info

- name: Installs a basic code env
  dss_code_env:
    connect_to: "{{dss_connection_info}}"
    name: basic-machine-learning
    deployment_mode: DESIGN_MANAGED
    lang: PYTHON
    owner: admin
    python_interpreter: PYTHON36
    package_list:
    - scikit-learn>=0.20,<0.21
    - scipy>=1.1,<1.2
    - xgboost==0.81
    - statsmodels>=0.9,<0.10
    - jinja2>=2.10,<2.11
    - flask>=1.0,<1.1

- name: Add some permissions
  dss_code_env:
    connect_to: "{{dss_connection_info}}"
    name: basic-machine-learning
    usable_by_all: false
    permissions:
    - group: data-team
      manageUsers: false
      update: true
      use: true
"""

RETURN = """
dss_code_env:
    description: Return current status of the infra
    type: dict
message:@
    description: CREATED, DELETED, MODIFIED or UNCHANGED
    type: str
"""



def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module

   #     Fields that can be updated in design node:

   #     * env.permissions, env.usableByAll, env.desc.owner
   #     * env.specCondaEnvironment, env.specPackageList, env.externalCondaEnvName, env.desc.installCorePackages,
   #       env.desc.installJupyterSupport, env.desc.yarnPythonBin

   #     Fields that can be updated in automation node (where {version} is the updated version):

   #     * env.permissions, env.usableByAll, env.owner
   #     * env.{version}.specCondaEnvironment, env.{version}.specPackageList, env.{version}.externalCondaEnvName, 
   #       env.{version}.desc.installCorePackages, env.{version}.desc.installJupyterSupport, env.{version}.desc.yarnPythonBin

   # [ "version" { ]
   #   permissions, usableByAll, owner, specCondaEnvironement, specPackageList, externalCondaEnvName
   # desc(installCorePackages,installJupyterSupport, yarnPythonbin)
   # [ } ]
    module_args = dict(
        state=dict(type="str", required=False, default="present"),
        name=dict(type="str", required=True),
        lang=dict(type="str", required=True),
        deployment_mode=dict(type="str", required=False, default=None),
        version=dict(type="str", required=False, default=None),
        core_packages=dict(type="bool", required=False, default=True),
        jupyter_support=dict(type="bool", required=False, default=True),
        update=dict(type="bool", required=False, default=True),
        permissions=dict(type="list", required=False, default=None),
        usable_by_all=dict(type="bool", required=False, default=None),
        owner=dict(type="str", required=False, default=None),
        conda_environment=dict(type="str", required=False, default=None),
        package_list=dict(type="list", required=False, default=None),
        external_conda_env_name=dict(type="str", required=False, default=None),
        python_interpreter=dict(type="str", required=False, default=None),
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
    
    required_code_env_def = {}
    versioned_required_code_env_def = required_code_env_def
    if args.version is not None:
        required_code_env_def[args.version] = {"desc":{}}
        versioned_required_code_env_def = required_code_env_def[args.version]
    else:
        required_code_env_def["desc"] = {}
    if args.permissions is not None:
        required_code_env_def["permissions"] = args.permissions
    if args.usable_by_all is not None:
        required_code_env_def["usableByAll"] = args.usable_by_all
    if args.conda_environment is not None:
        versioned_required_code_env_def["specCondaEnvironment"] = args.conda_environment
    if args.package_list is not None:
        versioned_required_code_env_def["specPackageList"] = "\n".join(args.package_list)
    if args.external_conda_env_name is not None:
        versioned_required_code_env_def["externalCondaEnvName"] = args.external_conda_env_name
    if args.owner is not None:
        if args.deployment_mode in ["DESIGN_MANAGED", "DESIGN_MANAGED", "PLUGIN_MANAGED", "PLUGIN_NON_MANAGED"]:
            versioned_required_code_env_def["desc"]["owner"] = args.owner
        else:
            versioned_required_code_env_def["owner"] = args.owner
    if args.desc is not None:
        update(versioned_required_code_env_def["desc"], args.desc)

    if args.core_packages and "installCorePackages" not in versioned_required_code_env_def["desc"]:
        versioned_required_code_env_def["desc"]["installCorePackages"] = args.core_packages

    if args.jupyter_support and "installJupyterSupport" not in versioned_required_code_env_def["desc"]:
        versioned_required_code_env_def["desc"]["installJupyterSupport"] = args.jupyter_support

    update_packages = False

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
            if args.version is not None:
                if "specPackageList" in versioned_required_code_env_def and args.version in code_env_def and "specPackageList" in code_env_def[args.version] and versioned_required_code_env_def["specPackageList"] != code_env_def[args.version]["specPackageList"]:
                    update_packages = True
                if "installJupyterSupport" in versioned_required_code_env_def["desc"] and "installJupyterSupport" in code_env_def[args.version]["desc"] and versioned_required_code_env_def["desc"]["installJupyterSupport"] != code_env_def[args.version]["desc"]["installJupyterSupport"]:
                    update_packages = True
            else:
                if "specPackageList" in required_code_env_def and "specPackageList" in code_env_def and required_code_env_def["specPackageList"] != code_env_def["specPackageList"]:
                    update_packages = True
                if "installJupyterSupport" in required_code_env_def["desc"] and "installJupyterSupport" in code_env_def["desc"] and required_code_env_def["desc"]["installJupyterSupport"] != code_env_def["desc"]["installJupyterSupport"]:
                    update_packages = True
    
        new_code_env_def = copy.deepcopy(code_env_def)
        update(new_code_env_def, required_code_env_def)

        # Prepare the result for dry-run mode
        result["changed"] = create or (exists and args.state == "absent") or (args.state == "present" and new_code_env_def != code_env_def)
        if result["changed"]:
            if create:
                result["message"] = "CREATED"
            elif exists:
                if args.state == "absent":
                    result["message"] = "DELETED"
                else:
                    if code_env_def != new_code_env_def:
                        result["message"] = "MODIFIED"
                    else:
                        result["message"] = "UNMODIFIED"

        if module.check_mode:
            module.exit_json(**result)

        # Apply the changes
        if args.state == "present":
            if create:
                if args.deployment_mode is None:
                    raise Exception("The argument deployment_mode is mandatory to create a code env")
                if args.python_interpreter is not None:
                    versioned_required_code_env_def["pythonInterpreter"] = args.python_interpreter
                code_env = client.create_code_env(args.lang, args.name, args.deployment_mode, required_code_env_def)
                code_env_def = code_env.get_definition()
                new_code_env_def = copy.deepcopy(code_env_def)
                update(new_code_env_def, required_code_env_def)

            if new_code_env_def != code_env_def:
                code_env.set_definition(new_code_env_def)

            if args.update or create or update_packages:
                code_env.update_packages()

            if args.jupyter_support:
                code_env.set_jupyter_support(args.jupyter_support)

            code_env_def = code_env.get_definition()
            result["dss_code_env"] = code_env_def

            if new_code_env_def != code_env_def:
                result["changed"] = True

        if args.state == "absent" and exists:
            if exists:
                code_env.delete()

        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg="{}\n\n{}\n\n{}".format(str(e), traceback.format_exc(), "".join(traceback.format_stack())))


def main():
    run_module()


if __name__ == "__main__":
    main()
