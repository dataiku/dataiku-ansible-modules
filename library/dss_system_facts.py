#!/usr/bin/env python

from __future__ import absolute_import
ANSIBLE_METADATA = {
    'metadata_version': '1.1',
    'status': ['preview'],
    'supported_by': 'dataiku-ansible-modules'
}

DOCUMENTATION = '''
---
module: dss_system_facts

short_description: Creates/get content of DATADIR/install.ini

description:
    - This module reads a datadir and returns the info in install.ini

options:
    datadir:
        description:
            - The datadir where DSS is installed. Be mindful to become the applicative user to call this module.
        required: true
author:
    - Jean-Bernard Jansen (jean-bernard.jansen@dataiku.com)
'''

EXAMPLES = '''
# Creates and displays a key with a label
- name: Get DSS system info
  become: true
  become_user: dataiku
  dss_system_facts:
    datadir: /home/dataiku/dss
  register: dss_system_info
- name: Debug
  debug:
    var: dss_system_info
'''

RETURN = '''
intall_ini:
    description: Parsed content
    type: dict
raw_install_ini:
    description: Raw content of the install.ini file
    type: str
'''

from ansible.module_utils.basic import AnsibleModule
import copy
import traceback
import os
import six.moves.configparser
import imp
import logging
import subprocess
import json

# Tricj to expose dictionary as python args
class MakeNamespace(object):
    def __init__(self,values):
        self.__dict__.update(values)

def run_module():
    # define the available arguments/parameters that a user can pass to
    # the module
    module_args = dict(
        datadir=dict(type='str', required=True),
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    args = MakeNamespace(module.params)

    try:
        if not os.path.isdir(args.datadir):
            module.fail_json(msg="Datadir '{}' not found.".format(args.datadir))
        
        current_uid = os.getuid()
        current_datadir_uid = os.stat(args.datadir).st_uid
        if current_uid != current_datadir_uid:
            module.fail_json(msg="dss_system_facts MUST run as the owner of the datadir (ran as UID={}, datadir owned by UID={})".format(current_uid, current_datadir_uid))

        # Setup the log
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', filename="{}/run/ansible.log".format(args.datadir),filemode="a")

        # Read the port
        config = six.moves.configparser.RawConfigParser()

        raw_install_ini = None
        with open("{}/install.ini".format(args.datadir),"r") as install_ini_file:
            raw_install_ini = install_ini_file.read()

        install_ini = {}
        config.read("{}/install.ini".format(args.datadir))
        for section in config.sections():
            install_ini[section] = {}
            for option in config.options(section):
                install_ini[section][option] = config.get(section, option)
        
        # Build result
        result = dict(
            changed=False,
            install_ini=install_ini,
            raw_install_ini=raw_install_ini,
        )

        module.exit_json(**result)
    except Exception as e:
        module.fail_json(msg="{}\n\n{}\n\n{}".format(str(e),traceback.format_exc(e),"".join(traceback.format_stack())))

def main():
    run_module()

if __name__ == '__main__':
    main()
