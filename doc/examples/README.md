Dataiku ansible modules examples
================================

This directory contains single file playbooks to show off the various modules. The modules library is referencend directly in `ansible.cfg`, but in real playbooks, the good way is to reference `dataiku-ansible-modules` as a dependency of your own roles.


# Examples

## Multi-node Design/Automation/API stack

This playbooks takes in a simple inventory of 4 nodes and deploys a Design node, an Automation node and 2 API Nodes, on for Development and on for Production. See the playbook file  `api_deployer_infra.yml` header for more details.

