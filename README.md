Dataiku DSS modules
===================

This role packages custom modules to administrate Dataiku Data Science Studio platforms.

Requirements
------------

These modules require the Dataiku DSS API to be installed and available in the Python runtime executing the module. The `ansible_python_interpreter` option might be useful when using a virtualenv.

Installation
------------

## Basic

If the first directory of your roles path is writable, just use:

 ```
ansible-galaxy install git+https://github.com/dataiku/dataiku-ansible-modules
 ```

Or specify the path in which you want the role to be installed:

 ```
ansible-galaxy install git+https://github.com/dataiku/dataiku-ansible-modules --roles-path=/path/to/your/roles
 ```

## Force update

If the role already exists, `ansible-galaxy` wont update it unless you the `--force` flag.

## Automation and versioning

You can use a `yaml` file with a content like this:

```YAML
---
- src: git+https://github.com/dataiku/dataiku-ansible-modules
  name: dataiku-ansible-modules
  version: master
```

Then install it like this:

```
ansible-galaxy install -r /path/to/your/file.yml
```

This allows you to:
- Force a specific version
- Rename the role on the fly

Example playbook
----------------

```YAML
- hosts: servers
  become: true
  become_user: dataiku
  roles:
     - dataiku-dss-modules # Makes the modules available
  tasks:
    - dss_get_credentials:
        datadir: /home/dataiku/dss
        api_key_name: myadminkey
      register: dss_connection_info

    - dss_group:
        connect_to: "{{dss_connection_info}}"
        name: datascienceguys

    - dss_user:
        connect_to: "{{dss_connection_info}}"
        login: myadmin
        password: theadminpasswordveryverystrongindeed
        groups: [administrators,datascienceguys]

    - dss_general_settings:
        connect_to: "{{dss_connection_info}}"
        settings:
          limits:
            attachmentBytes:
              hard: -1
              soft: -1
            memSampleBytes:
              hard: 524288000
              soft: 104857600
            shakerMemTableBytes:
              hard: 524288000
              soft: -1
```

License
-------

Apache 2.0
