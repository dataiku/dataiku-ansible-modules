from __future__ import absolute_import

import collections
import logging
import os

import six
from ansible.module_utils.dataikuapi.dssclient import DSSClient


class MakeNamespace(object):
    def __init__(self, values):
        self.__dict__.update(values)


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
            extracted_data[k] = extract_keys(input_data.get(k,{}), v)
        else:
            extracted_data[k] = input_data.get(k, None)
    return extracted_data
