Dataiku DSS modules
===================

This role packages custom modules to administrate Dataiku Data Science Studio platforms.

Requirements
------------

These modules require the Dataiku DSS API to be installed and available in the Python runtime executing the module. The `ansible_python_interpreter` option might be useful when using a virtualenv.

Example Playbook
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
