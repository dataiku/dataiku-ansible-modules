#!/usr/bin/env python2

from __future__ import absolute_import

import copy
import traceback

import ansible.module_utils.dataiku_api_preload_imports
import six
from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.dataiku_utils import MakeNamespace, add_dss_connection_args, get_client_from_parsed_args
from ansible.module_utils.dataikuapi.dss.admin import DSSUser
from ansible.module_utils.dataikuapi.utils import DataikuException
from requests.exceptions import HTTPError

ANSIBLE_METADATA = {"metadata_version": "1.1", "status": ["preview"], "supported_by": "dataiku-ansible-modules"}

DOCUMENTATION = """
---
module: dss_user

short_description: Creates, edit or delete a Data Science Studio user 

description:
    - "This module edits a complete user profile. If the user does not exist and is required to, it is created. If the user exists but is supposed not to, it deleted"

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
            - The port on which to make the requests.
        required: false
        default: 80
    api_key:
        description:
            - The API Key to authenticate on the API. Mandatory if connect_to is not used
        required: false
    login:
        description:
            - The login name of the user
        required: true
    password:
        description:
            - The unencrypted password of the user. Mandatory if the user must be created
        required: false
    set_password_at_creation_only:
        description:
            - Allow not to change the password to the requested one if the user already exists. This is
              the only way to actually achieve idempotency, so it is true by default. If set to false, the task
              will always have the "changed" status because we cannot check if the password was actually different before
              or not
        default: true
        required: false
    email:
        description:
            - The email of the user
        required: false
    display_name:
        description:
            - The display name for the user. Defaults to the login at creation.
        required: false
    groups:
        description:
            - The list of groups the user belongs to. If not set at creation, defaults to ["readers"]
        default: empty
        required: false
    profile:
        description:
            - The profile type of the user. Mandatory if the user must be created
        default: READER
        required: false
    source_type:
        description:
            - The source type of the user, either LOCAL, LDAP or LOCAL_NO_AUTH
        required: false
        default: LOCAL
    state:
        description:
            - Wether the user is supposed to exist or not. Possible values are "present" and "absent"
        default: present
        required: false

author:
    - Jean-Bernard Jansen (jean-bernard.jansen@dataiku.com)
"""

EXAMPLES = """
# Creates a user using dss_get_credentials if you have SSH Access
- name: Get the API Key
  become: true
  become_user: dataiku
  dss_get_credentials:
    datadir: /home/dataiku/dss
    api_key_name: myadminkey
  register: dss_connection_info
- name: Add a user  
  become: true
  become_user: dataiku
  dss_user:
    connect_to: "{{dss_connection_info}}"
    login: user1
    display_name: Robert
    password: Robert
    groups:
      - readers
    profile: DATA_SCIENTIST

# Creates a user using explicit host/port/key
# Force the password to be set everytime - always return as a change
- name: Add a user  
  delegate_to: localhost
  dss_user:
    host: 192.168.0.2
    port: 80
    api_key: XXXXXXXXXXXXXX
    login: user2
    display_name: Marcel
    password: Marcel
    set_password_at_creation_only: false

# Delete a user
- name: Add a user  
  become: true
  become_user: dataiku
  dss_user:
    connect_to: "{{dss_connection_info}}"
    login: user1
    state: absent
"""

RETURN = """
previous_user_def:
    description: The previous values
    type: dict
user_def:
    description: The current values is the group have not been deleted
    type: dict
message:
    description: CREATED, MODIFIED, UNCHANGED or DELETED 
    type: str
"""



def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        login=dict(type="str", required=True),
        password=dict(type="str", required=False, default=None, no_log=True),
        set_password_at_creation_only=dict(type="bool", required=False, default=True),
        email=dict(type="str", required=False, default=None),
        display_name=dict(type="str", required=False, default=None),
        groups=dict(type="list", required=False, default=None),
        profile=dict(type="str", required=False, default=None),
        source_type=dict(type="str", required=False, default="LOCAL"),
        state=dict(type="str", required=False, default="present"),
    )
    add_dss_connection_args(module_args)

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    args = MakeNamespace(module.params)
    if args.state not in ["present", "absent"]:
        module.fail_json(
            msg="Invalid value '{}' for argument state : must be either 'present' or 'absent'".format(args.state)
        )

    result = dict(changed=False, message="UNCHANGED",)

    try:
        client = get_client_from_parsed_args(module)
        user = DSSUser(client, args.login)
        user_exists = True
        create_user = False
        current_user = None
        try:
            current_user = user.get_definition()
        except DataikuException as e:
            if str(e).startswith("com.dataiku.dip.server.controllers.NotFoundException"):
                user_exists = False
                if args.state == "present":
                    create_user = True
            else:
                raise
        except:
            raise

        # Manage errors
        if args.source_type not in ["LOCAL", "LDAP", "LOCAL_NO_AUTH"]:
            module.fail_json(
                msg="Invalid value '{}' for source_type : must be either 'LOCAL', 'LDAP' or 'LOCAL_NO_AUTH'".format(
                    args.source_type
                )
            )
        if args.password is None and create_user and args.source_type not in ["LDAP", "LOCAL_NO_AUTH"]:
            module.fail_json(
                msg="The 'password' parameter is missing but is mandatory to create new local user '{}'.".format(
                    args.login
                )
            )
        if args.display_name is None and create_user:
            # module.fail_json(msg="The 'display_name' parameter is missing but is mandatory to create new user '{}'.".format(args.login))
            # TODO: shall we fail here or use a default to login ?
            args.display_name = module.params["display_name"] = args.login
        if args.groups is None and create_user:
            args.groups = module.params["groups"] = ["readers"]

        # Build the new user definition
        # TODO: be careful that the key names changes between creation and edition
        new_user_def = copy.deepcopy(current_user) if user_exists else {}  # Used for modification
        result["previous_user_def"] = copy.deepcopy(new_user_def)
        for key, api_param in [
            ("email", "email"),
            ("display_name", "displayName"),
            ("profile", "userProfile"),
            ("groups", "groups"),
            ("source_type", "sourceType"),
        ]:
            if module.params.get(key, None) is not None:
                value = module.params[key]
                if isinstance(value, six.binary_type):
                    value = value.decode("UTF-8")
                new_user_def[key if create_user else api_param] = value
        if user_exists and args.password is not None and not args.set_password_at_creation_only:
            new_user_def["password"] = args.password

        # Sort groups list before comparison as they should be considered sets
        new_user_def.get("groups", []).sort()
        if user_exists:
            current_user.get("groups", []).sort()

        # Prepare the result for dry-run mode
        result["changed"] = (
            create_user or (user_exists and args.state == "absent") or (user_exists and current_user != new_user_def)
        )
        if result["changed"]:
            if create_user:
                result["message"] = "CREATED"
            elif user_exists:
                if args.state == "absent":
                    result["message"] = "DELETED"
                elif current_user != new_user_def:
                    result["message"] = "MODIFIED"

        # Can be useful to register info from a playbook and act on it
        if args.state == "present":
            result["user_def"] = new_user_def

        if module.check_mode:
            module.exit_json(**result)

        # Apply the changes
        if result["changed"]:
            if create_user:
                create_excluded_keys = ["email"]
                create_excluded_values = {}
                for create_excluded_key in create_excluded_keys:
                    if new_user_def.get(create_excluded_key, None) is not None:
                        create_excluded_values[create_excluded_key] = new_user_def[create_excluded_key]
                        del new_user_def[create_excluded_key]
                new_user = client.create_user(args.login, args.password, **new_user_def)
                if module.params.get("email", None) is not None:
                    new_user_def_mod = new_user.get_definition()
                    new_user_def_mod.update(create_excluded_values)
                    new_user.set_definition(new_user_def_mod)
            elif user_exists:
                if args.state == "absent":
                    user.delete()
                elif current_user != new_user_def:
                    result["message"] = str(user.set_definition(new_user_def))

        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg="{}\n\n{}\n\n{}".format(str(e), traceback.format_exc(), "".join(traceback.format_stack())))


def main():
    run_module()


if __name__ == "__main__":
    main()
