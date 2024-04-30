from __future__ import absolute_import

import collections
import logging
import os
import traceback

import six
from ansible.module_utils.basic import missing_required_lib
from ansible.module_utils.dataikuapi.dssclient import DSSClient

# Import Error handling required du to ansible sanity checks handling of non-default python libraries
# https://docs.ansible.com/ansible/latest/dev_guide/testing/sanity/import.html
try:
    from packaging import version
except ImportError:
    version = None
    HAS_PACKAGING_LIBRARY = False
    PACKAGING_IMPORT_ERROR = traceback.format_exc()
else:
    HAS_PACKAGING_LIBRARY = True
    PACKAGING_IMPORT_ERROR = None


class MakeNamespace(object):
    def __init__(self, values):
        self.__dict__.update(values)


def is_version_more_recent(module, input_version, baseline):
    if not HAS_PACKAGING_LIBRARY:
        module.fail_json(
            msg=missing_required_lib("packaging"),
            exception=PACKAGING_IMPORT_ERROR
        )
    else:
        input_version = version.parse(input_version)
        baseline = version.parse(baseline)
        return input_version > baseline


def add_dss_connection_args(module_args):
    module_args.update(
        {
            "connect_to": dict(type="dict", required=False, default={}, no_log=True),
            "host": dict(type="str", required=False, default="127.0.0.1"),
            "port": dict(type="str", required=False, default=None),
            "api_key": dict(type="str", required=False, default=None),
        }
    )


def get_client_from_parsed_args(module):
    args = MakeNamespace(module.params)
    api_key = (
        args.api_key
        if args.api_key is not None
        else args.connect_to.get("api_key", os.environ.get("DATAIKU_ANSIBLE_DSS_API_KEY", None))
    )
    if api_key is None:
        module.fail_json(
            msg="Missing an API Key, either from 'api_key' parameter, 'connect_to' parameter or DATAIKU_ANSIBLE_DSS_API_KEY env var".format(
                args.state
            )
        )
    port = (
        args.port
        if args.port is not None
        else args.connect_to.get("port", os.environ.get("DATAIKU_ANSIBLE_DSS_PORT", "80"))
    )
    host = args.host
    client = DSSClient("http://{}:{}".format(args.host, port), api_key=api_key)
    return client


# Similar to dict.update but deep
def update(d, u):
    if isinstance(d, collections.Mapping):
        for k, v in six.iteritems(u):
            if isinstance(v, collections.Mapping):
                d[k] = update(d.get(k, {}), v)
            else:
                d[k] = v
    else:
        d = u
    return d


def extract_keys(input_data, keys_reference):
    if isinstance(input_data, collections.Mapping):
        extracted_data = {}
        for k, v in keys_reference.items():
            if isinstance(v, collections.Mapping):
                extracted_data[k] = extract_keys(input_data.get(k,{}), v)
            else:
                extracted_data[k] = input_data.get(k, None)
    else:
        extracted_data = input_data
    return extracted_data
