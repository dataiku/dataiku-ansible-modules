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
module: dss_plugin

short_description: Installs a plugin

description:
    This tasks installs a plugin from the store by default. It installs from a git repository if a repository
    is specified. This task does not check all the way the installed plugin comes from the source specified here.
    It is considered installed if already present in DSS.

    This task can be used to fetch facts about an installed plugin.

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
    plugin_id:
        description;
            - ID of the plugin
        required: False
    zip_file:
        description:
            - Path to Zip file
        required: False
    git_repository_url:
        description:
            - URL of the git repository
        required: False
    git_checkout:
        description:
            - Revision to checkout
        required: False
        default: master
    git_subpath:
        description:
            - Subpath in the repo where to find the plugin
        required: False
        default: None
    state:
        description:
            - Is the plugin is supposed to be there or not. Either "present" or "absent". Default "present"
              WARNING: absent is only supported in check mode, not implemented for real.
        required: false
    force_update:
        description:
            - Force an update based on describes sources even if already installed
        required: false
author:
    - Jean-Bernard Jansen (jean-bernard.jansen@dataiku.com)
"""

EXAMPLES = """
"""

RETURN = """
dss_plugin:
    description: Return resulting status of the plugin
    type: dict
message:
    description: CREATED, DELETED, MODIFIED or UNMODIFIED
    type: str
"""



def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        state=dict(type="str", required=False, default="present"),
        plugin_id=dict(type="str", required=True),
        zip_file=dict(type="str", required=False, default=None),
        git_repository_url=dict(type="str", required=False, default=None),
        git_checkout=dict(type="str", required=False, default="master"),
        git_subpath=dict(type="str", required=False, default=None),
        settings=dict(type="dict", required=False, default={}),
        force_update=dict(type="bool", required=False, default=False),
    )
    add_dss_connection_args(module_args)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    args = MakeNamespace(module.params)

    result = dict(changed=False, message="UNCHANGED",)

    client = None
    exists = False
    create = False
    plugin = None
    current_settings = {}
    try:
        client = get_client_from_parsed_args(module)
        plugins = client.list_plugins()
        plugin_dict = { plugin['id']: plugin for plugin in plugins }

        # Check existence
        if args.plugin_id in plugin_dict:
            exists = True

        if not exists and args.state == "present":
            create = True

        if exists:
            plugin = client.get_plugin(args.plugin_id)
            current_settings = copy.deepcopy(plugin.get_settings().get_raw())

        # Prepare the result for dry-run mode
        new_settings = copy.deepcopy(current_settings)
        if args.settings is not None:
            update(new_settings, args.settings)
        
        result["changed"] = create or (exists and (args.state == "absent" or (args.settings is not None and new_settings != current_settings)))
        if result["changed"]:
            if create:
                result["message"] = "CREATED"
            elif exists:
                if args.state == "absent":
                    result["message"] = "DELETED"
                elif args.settings is not None:
                    result["message"] = "MODIFIED"
                else:
                    result["message"] = "UNMODIFIED"

        result["dss_plugin"] = {
            "id": args.plugin_id,
        }
        if exists:
            result["dss_plugin"]["settings"] = new_settings
            update(result["dss_plugin"], plugin_dict[args.plugin_id])

        if module.check_mode:
            module.exit_json(**result)

        # Apply the changes
        if args.state == "present":
            if not exists:
                future = None
                if args.zip_file is not None:
                    pass
                elif args.git_repository_url is not None:
                    pass
                else:
                    # Install from store
                    future = client.install_plugin_from_store(args.plugin_id)
                future.wait_for_result()
                plugin = client.get_plugin(args.plugin_id)
                current_settings = copy.deepcopy(plugin.get_settings().get_raw())
                new_settings = copy.deepcopy(current_settings)
                if args.settings is not None:
                    update(new_settings, args.settings)
            elif args.force_update:
                future = None
                if args.zip_file is not None:
                    pass
                elif args.git_repository_url is not None:
                    pass
                else:
                    # Install from store
                    future = plugin.update_from_store()
                future.wait_for_result()
                plugin = client.get_plugin(args.plugin_id)

        if args.settings is not None and args.state == "present" and new_settings != current_settings:
            settings_handle = plugin.get_settings()
            update(settings_handle.settings, new_settings)

            print("Yaye")
            settings_handle.save()

        if args.state == "absent" and exists:
            raise "Plugin deletion not supported yet."

        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg="{}\n\n{}\n\n{}".format(str(e), traceback.format_exc(), "".join(traceback.format_stack())))


def main():
    run_module()

if __name__ == "__main__":
    main()