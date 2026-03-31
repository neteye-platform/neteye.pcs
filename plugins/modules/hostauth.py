from ansible.module_utils.basic import AnsibleModule
from ansible_collections.neteye.pcs.plugins.module_utils.cluster import isAlreadyCluster
from typing import Union

__metaclass__ = type

DOCUMENTATION = r"""
---
module: hostauth

short_description: Authenticates a host within a pcs cluster

version_added: "1.0.0"

description: Given a hostname, it will authenticate it to a pcs cluster.

options:
    host:
        description: FQDN of the host to add
        required: true
        type: str
    password_file:
        description: Path to the file with the password of hacluster user
        required: true
        type: path
    username:
        description: Username used for the authentication
        required: false
        type: str
        default: hacluster
"""

EXAMPLES = r"""
- name: Add hosts to cluster
  neteye.pcs.hostauth:
    host: neteye-cluster1.neteyelocal
    password_file: "/root/.pwd_hacluster"
"""

RETURN = r"""
original_host:
    description: The original hostname.
    type: str
    returned: always
    sample: 'neteye-cluster1.neteyelocal'
cluster_already_created:
    description: If cluster is already created, it fails.
    type: bool
    returned: always
    sample: false
"""


def getPassword(path: str) -> Union[None, str]:
    try:
        with open(path, "r") as passwordFile:
            password = passwordFile.read().strip()
        return password
    except FileNotFoundError:
        return None


def run_module():
    module_args = dict(
        host=dict(type="str", required=True),
        password_file=dict(type="path", required=True, no_log=True),
        username=dict(type="str", required=False, default="hacluster"),
    )

    result = dict(
        changed=False,
        original_host=module_args["host"],
        cluster_already_created=False,
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    hostname = module.params["host"]
    username = module.params["username"]
    password_file = module.params["password_file"]

    # check if a cluster is already created
    result["cluster_already_created"] = isAlreadyCluster(module)

    # check if host is already authed
    cmd = ["pcs", "pcsd", "status", hostname]
    rc, _, _ = module.run_command(args=cmd)
    result["changed"] = rc != 0

    # exit if was already created
    if not result["changed"]:
        module.exit_json(**result)

    if result["cluster_already_created"] and result["changed"]:
        module.fail_json(
            msg="Add a node to a existing cluster is not supported!", **result
        )

    # retrieve password from file
    password = getPassword(password_file)

    if password is None:
        module.fail_json(msg="Hacluster password file does not exists!", **result)
    if password == "":
        module.fail_json(msg="Hacluster password file is empty!", **result)

    # exit if checkmode
    if module.check_mode:
        module.exit_json(**result)

    # try to auth the host
    cmd = ["pcs", "host", "auth", hostname, "-u", username, "-p", password]
    rc, _, stderr = module.run_command(args=cmd)
    if rc != 0:
        module.fail_json(msg=f"Couldn't auth the node, {stderr}", **result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
