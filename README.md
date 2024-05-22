Dataiku DSS modules (Archived)
==============================

:warning This project is deprecated in favor of the [Dataiku Ansible Collection](https://github.com/dataiku/dataiku-ansible-collection)

This role packages custom modules to administrate Dataiku Data Science Studio platforms.


Installation
------------

## Basic

If the first directory of your roles path is writable, just use:

 ```
ansible-galaxy install git+https://github.com/dataiku/dataiku-api-client-python,release/8.0
ansible-galaxy install git+https://github.com/dataiku/dataiku-ansible-modules
 ```

Or specify the path in which you want the role to be installed:

 ```
ansible-galaxy install git+https://github.com/dataiku/dataiku-api-client-python,release/8.0 --roles-path=/path/to/your/roles
ansible-galaxy install git+https://github.com/dataiku/dataiku-ansible-modules --roles-path=/path/to/your/roles
 ```

## Force update

If the role already exists, `ansible-galaxy` wont update it unless you the `--force` flag.

## Automation and versioning

You can use a `yaml` file with a content like this:

```YAML
---
- src: git+https://github.com/dataiku/dataiku-api-client-python
  name: dataiku-api-client-python
  version: release/8.0
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

Basic use
---------

To have the modules available in your own roles, provided the role is in your role path, you can add the role as a dependency of your own. Reference it in the `meta/main.yml` file of your role:

```YAML
---
dependencies:
 - dataiku-ansible-modules
```

Alternatively, a less ansiblish way is to add the `library` subdirectory of this role in the modules path.

Example playbook
----------------

Find some more examples [here](doc/examples/).

```YAML
- hosts: servers
  become: true
  become_user: dataiku
  roles:
     - dataiku-ansible-modules # Makes the modules available
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
          ldapSettings:
            enabled: true
            url: ldap://ldap.internal.example.com/dc=example,dc=com
            bindDN: uid=readonly,ou=users,dc=example,dc=com
            bindPassword: theserviceaccountpassword
            useTls: true
            autoImportUsers: true
            userFilter: (&(objectClass=posixAccount)(uid={USERNAME}))
            defaultUserProfile: READER
            displayNameAttribute: gecos
            emailAttribute: mail
            enableGroups: true
            groupFilter: (&(objectClass=posixGroup)(memberUid={USERDN}))
            groupNameAttribute: cn
            groupProfiles: []
            authorizedGroups: dss-users
```

License
-------

Apache 2.0
