import re

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.neteye.pcs.plugins.module_utils.cluster import (
    CLUSTER_FILE_PATH,
    isAlreadyCluster,
)

__metaclass__ = type

DOCUMENTATION = r"""
---
module: quorum

short_description: Manages cluster qdevice

version_added: "1.0.0"

description: Creates, destroy or ensure the presence of a cluster quorum device

options:
    host:
        description: hostname of the qdevice
        required: false
        type: str
    state:
        description: hostname of the qdevice
        required: true
        type: str
        choices: ['present', 'absent']
    algorithm:
        description: algorithm to use
        required: false
        type: str
        default: ffsplit
        choices: ['ffsplit', 'lms']
"""

EXAMPLES = r"""
- name: setup qdevice
  neteye.pcs.quorum:
    host: neteye-cluster3.neteyelocal
    state: present
    algorithm: ffsplit

- name: remove qdevice
  neteye.pcs.quorum:
    state: absent
"""

RETURN = r"""
cluster_already_created:
    description: If cluster is already created, it fails.
    type: bool
    returned: always
    sample: false
qdevice_already_present:
    description: whether qdevice was present
    type: bool
    returned: always
    sample: true
hostname:
    description: the hostname of the qdevice
    type: str
    returned: always
    sample: neteye-cluster3.neteyelocal
algorithm:
    description: the algorithm used for the qdevice
    type: str
    returned: always
    sample: ffsplit
"""


def isQdevicePresent(module: AnsibleModule) -> bool:
    cmd = ["pcs", "quorum", "device", "status"]
    rc, _, _ = module.run_command(args=cmd)
    return rc == 0


def findQdeviceHostname() -> str:
    try:
        with open(CLUSTER_FILE_PATH, "r") as corosync_conf:
            qdevice_defined = re.compile(r"device\s*\{([^}]+)\}", re.M + re.S)
            re_qdevice_defined = qdevice_defined.findall(corosync_conf.read())
    except IOError:
        return ""
    qdevice_name = re.compile(r"host\s*:\s*([\w.-]+)\s*", re.M)
    return qdevice_name.findall(re_qdevice_defined[0])[0]


def findQdeviceAlgorithm() -> str:
    try:
        with open(CLUSTER_FILE_PATH, "r") as corosync_conf:
            qdevice_defined = re.compile(r"device\s*\{([^}]+)\}", re.M + re.S)
            re_qdevice_defined = qdevice_defined.findall(corosync_conf.read())
    except IOError:
        return ""
    algorithm_name = re.compile(r"algorithm\s*:\s*([\w.-]+)\s*", re.M)
    return algorithm_name.findall(re_qdevice_defined[0])[0]


def run_module():
    module_args = dict(
        host=dict(type="str", required=False),
        state=dict(
            type="str",
            required=True,
            choices=["present", "absent"],
        ),
        algorithm=dict(
            type="str", required=False, default="ffsplit", choices=["ffsplit", "lms"]
        ),
    )

    result = dict(
        changed=False,
        cluster_already_created=False,
        qdevice_already_present=False,
        host="",
        algorithm="",
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    host = module.params["host"]
    state = module.params["state"]
    algorithm = module.params["algorithm"]

    result["cluster_already_created"] = isAlreadyCluster(module)

    if not result["cluster_already_created"]:
        module.fail_json(msg="You are not in a cluster!", **result)

    result["qdevice_already_present"] = isQdevicePresent(module)

    # check provided information
    if result["qdevice_already_present"]:
        result["host"] = findQdeviceHostname()
        result["algorithm"] = findQdeviceAlgorithm()

        if host and result["host"] != host:
            module.fail_json(
                msg="Host provided is different from what in use", **result
            )
        if algorithm and result["algorithm"] != algorithm:
            module.fail_json(
                msg="Algorithm provided is different from what in use", **result
            )

    # delete old qdevice
    if result["qdevice_already_present"] and state == "absent":
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)

        cmd = ["pcs", "quorum", "device", "remove"]
        rc, _, stderr = module.run_command(args=cmd)
        if rc != 0:
            module.fail_json(msg=f"Couldn't delete the qdevice, {stderr}", **result)

    # create new qdevice
    elif not result["qdevice_already_present"] and state == "present":
        if not host:
            module.fail_json("You have to provide a hostname!", **result)

        # create the qdevice
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)

        cmd = [
            "pcs",
            "quorum",
            "device",
            "add",
            "model",
            "net",
            f"host={host}",
            f"algorithm={algorithm}",
        ]
        rc, _, stderr = module.run_command(args=cmd)
        if rc != 0:
            module.fail_json(msg=f"Couldn't add the qdevice, {stderr}", **result)

        result["host"] = host
        result["algorithm"] = algorithm

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
