import re

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.neteye.pcs.plugins.module_utils.cluster import (
    CLUSTER_FILE_PATH,
    isAlreadyCluster,
)
from typing import Tuple

__metaclass__ = type

DOCUMENTATION = r"""
---
module: cluster

short_description: Manage a pcs cluster

version_added: "1.0.0"

description: Ansible module to manage a pcs cluster

options:
    nodes:
        description: List of operational nodes to add to the cluster
        required: false
        type: list
    cluster_name:
        description: The name of the cluster
        required: false
        type: str
        default: NetEye
    force:
        description: Force recreation of the cluster
        required: false
        type: bool
        default: false
    state:
        description: State of the cluster
        required: true
        type: str
        choices: ['started', 'present', 'absent']
    enabled:
        description:
          - Ensures cluster is enabled (Note; if state is 'present', this variable is ignored)
          - NOTE; Idempotency issue, in this next part we don't check whether the state of the cluster is the same of the one we are setting, because we would have to check every single node and their daemon
        required: false
        type: bool
        default: true
"""

EXAMPLES = r"""
- name: Create my awesome cluster
  neteye.pcs.cluster:
    state: present
    nodes: [neteye-cluster1.neteyelocal, neteye-cluster2.neteyelocal]

- name: Force recreation of the cluster
  neteye.pcs.cluster:
    nodes: [neteye-cluster1.neteyelocal, neteye-cluster2.neteyelocal]
    force: true
    state: started
    enable: true

- name: Use inventory group as the list of nodes
  neteye.pcs.cluster:
    nodes: "{{ groups['nodes'] }}"
    state: started
    enable: true
"""

RETURN = r"""
cluster_already_created:
    description: If cluster is already created, it fails.
    type: bool
    returned: always
    sample: false
"""


def compareClusterNames(cluster_name: str) -> bool:
    with open(CLUSTER_FILE_PATH, "r") as cluster_file:
        cluster_file_lines = cluster_file.readlines()
        for line in cluster_file_lines:
            if re.search(r"cluster_name:", line):
                wordsInLine = line.strip().split()
                if cluster_name not in wordsInLine:
                    return False
                else:
                    return True
    return False


def compareClusterNodes(nodes: list) -> bool:
    with open(CLUSTER_FILE_PATH, "r") as cluster_file:
        cluster_file_content = cluster_file.read()
        if any(host not in cluster_file_content for host in nodes):
            return False
    return True


def checkAuthNodes(nodes: list, module: AnsibleModule) -> bool:
    for node in nodes:
        cmd = ["pcs", "pcsd", "status", node]
        rc, _, _ = module.run_command(args=cmd)
        if rc != 0:
            return False
    return True


def isClusterStarted(module: AnsibleModule) -> bool:
    cmd = ["pcs", "cluster", "status"]
    rc, _, _ = module.run_command(args=cmd)
    return rc == 0


def startCluster(module: AnsibleModule) -> bool:
    cmd = ["pcs", "cluster", "start", "--all"]
    rc, _, _ = module.run_command(args=cmd)
    return rc == 0


def setEnablingCluster(enableCluster: bool, module: AnsibleModule) -> Tuple[bool, str]:
    if enableCluster:
        cmd = ["pcs", "cluster", "enable", "--all"]
        rc, _, stderr = module.run_command(args=cmd)
        return (rc == 0, f"Couldn't enable the cluster, {stderr}")
    else:
        cmd = ["pcs", "cluster", "disable", "--all"]
        rc, _, stderr = module.run_command(args=cmd)
        return (rc == 0, f"Couldn't disable the cluster, {stderr}")


def run_module():
    module_args = dict(
        nodes=dict(type="list", required=False),
        cluster_name=dict(type="str", required=False, default="NetEye"),
        force=dict(type=bool, required=False, default=False),
        state=dict(
            type=str,
            required=True,
            choices=["started", "present", "absent"],
        ),
        enabled=dict(type=bool, required=False, default=True),
    )

    result = dict(
        changed=False,
        cluster_already_created=False,
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    nodes = module.params["nodes"]
    cluster_name = module.params["cluster_name"]
    force = module.boolean(module.params["force"])
    state = module.params["state"]
    enabled = module.boolean(module.params["enabled"])

    # only check if nodes are authenticated when nodes are passed
    if nodes:
        if not isinstance(nodes, list):
            module.fail_json(msg="Nodes must be a list!", **result)
        elif len(nodes) <= 1:
            module.fail_json(msg="A cluster must have more than one node!", **result)
        elif not checkAuthNodes(nodes, module):
            module.fail_json(
                msg="At least one of the provided nodes is not authenticated!", **result
            )

    # check if a cluster is already created
    if isAlreadyCluster(module):
        result["cluster_already_created"] = True

    if result["cluster_already_created"] and state == "absent":
        module.fail_json(
            "A cluster is already created, but removal is not supported by this module",
            **result,
        )

    # nothing to do
    if not result["cluster_already_created"] and state == "absent":
        module.exit_json(**result)

    # nothing to do
    if result["cluster_already_created"] and state == "present" and not force:
        module.exit_json(**result)

    # if we dont want to recerate the cluster, we check configuration
    if result["cluster_already_created"] and not force:
        if cluster_name and not compareClusterNames(cluster_name):
            module.fail_json(
                msg="A cluster with another name already exists!", **result
            )

        if nodes and isinstance(nodes, list) and not compareClusterNodes(nodes):
            module.fail_json(
                msg="Not every given node is part of the cluster!", **result
            )

    # create a new cluster
    if not result["cluster_already_created"] or force:
        result["changed"] = True

        if module.check_mode:
            module.exit_json(**result)

        cmd = ["pcs", "cluster", "setup"]
        if force:
            cmd.append("--force")
        cmd.append(cluster_name)
        for node in nodes:
            cmd.append(node)

        rc, _, _ = module.run_command(args=cmd)
        if rc != 0:
            module.fail_json(msg="Could not create the cluster", **result)

    # at this point the cluster is created and we have to check if user wants it started
    if state == "started" and not isClusterStarted(module):
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)

        if not startCluster(module):
            module.fail_json(msg="Could not start the cluster", **result)

    if module.check_mode:
        module.exit_json(**result)

    if state != "started":
        module.exit_json(**result)

    # NOTE: Idempotency issue: in this next part we dont check whether the
    # state of the cluster is the same of the one we are setting, because
    # we would have to check every single node and the status of their daemon

    rc, msg = setEnablingCluster(enabled, module)
    if not rc:
        module.fail_json(msg=msg, **result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
