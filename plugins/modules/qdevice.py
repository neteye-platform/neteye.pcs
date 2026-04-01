import os.path

from ansible.module_utils.basic import AnsibleModule
from typing import Tuple

__metaclass__ = type

DOCUMENTATION = r"""
---
module: resource

short_description: Manages local qdevice setting

version_added: "1.0.0"

description: Creates, destroy or ensure the presence of local qdevice

options:
    model:
        description: the name of the model
        required: false
        type: str
        default: net
    state:
        description: the state of the qdevice
        required: true
        type: str
        choices: ['present', 'absent', 'started', 'stopped']
    enabled:
        description:
          - whether the qdevice is enabled or not
          - ignored if state = 'present'
          - forced to false if state = 'absent'
        required: false
        type: bool
        default: true
"""

EXAMPLES = r"""
- name: Setup a new qdevice
  neteye.pcs.qdevice:
    model: net
    state: started
    enabled: true

- name: Delete qdevice
  neteye.pcs.qdevice:
    state: absent
"""

RETURN = r"""
qdevice_already_created:
    description: whether qdevice was already created
    type: bool
    returned: always
    sample: false
is_qdevice_started:
    description: whether qdevice is running
    type: bool
    returned: always
    sample: true
is_qdevice_enabled:
    description: whether qdevice is enabled
    type: bool
    returned: always
    sample: true
"""


def isQdevicePresent(qdeviceConfPath: str) -> bool:
    return os.path.isdir(qdeviceConfPath)


def isQdeviceStarted(model_name: str, module: AnsibleModule) -> bool:
    cmd = ["pcs", "qdevice", "status", model_name]
    rc, _, _ = module.run_command(args=cmd)
    return rc == 0


def setStartStatusQdevice(
    model_name: str, qdeviceHasToBeStarted: bool, module: AnsibleModule
) -> Tuple[bool, str]:
    qdeviceStarted = isQdeviceStarted(model_name, module)

    if not qdeviceStarted and qdeviceHasToBeStarted:
        cmd = ["pcs", "qdevice", "start", model_name]
        rc, _, stderr = module.run_command(args=cmd)
        return (rc == 0, stderr)
    elif qdeviceStarted and not qdeviceHasToBeStarted:
        cmd = ["pcs", "qdevice", "stop", model_name]
        rc, _, stderr = module.run_command(args=cmd)
        return (rc == 0, stderr)

    return (True, "")


def isQdeviceEnabled(module: AnsibleModule) -> bool:
    cmd = ["systemctl", "is-enabled", "--quiet", "corosync-qnetd.service"]
    rc, _, _ = module.run_command(args=cmd)
    return rc == 0


def setEnablingQdevice(
    model_name: str, qdeviceHasToBeEnabled: bool, module: AnsibleModule
) -> Tuple[bool, str]:
    qdeviceEnabled = isQdeviceEnabled(module)

    if not qdeviceEnabled and qdeviceHasToBeEnabled:
        cmd = ["pcs", "qdevice", "enable", model_name]
        rc, _, stderr = module.run_command(args=cmd)
        return (rc == 0, stderr)
    elif qdeviceEnabled and not qdeviceHasToBeEnabled:
        cmd = ["pcs", "qdevice", "disable", model_name]
        rc, _, stderr = module.run_command(args=cmd)
        return (rc == 0, stderr)

    return (True, "")


def run_module():
    module_args = dict(
        model=dict(type="str", required=False, default="net"),
        state=dict(
            type="str",
            required=True,
            choices=["present", "absent", "started", "stopped"],
        ),
        enabled=dict(type="bool", required=False, default=True),
    )

    result = dict(
        changed=False, qdevice_already_created=False, is_qdevice_started=False
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    model_name = module.params["model"]
    state = module.params["state"]
    enabled = module.boolean(module.params["enabled"])

    qdeviceConfPath = "/etc/corosync/qnetd/nssdb"
    result["qdevice_already_created"] = isQdevicePresent(qdeviceConfPath)

    # we have to remove the qdevice
    if result["qdevice_already_created"] and state == "absent":
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)

        result["is_qdevice_started"] = isQdeviceStarted(model_name, module)
        result["is_qdevice_enabled"] = isQdeviceEnabled(module)

        if not setEnablingQdevice(model_name, False, module):
            module.fail_json(msg="Couldn't disable the qdevice", **result)
        result["is_qdevice_enabled"] = False

        cmd = ["pcs", "qdevice", "destroy", model_name]
        rc, _, stderr = module.run_command(args=cmd)
        if rc != 0:
            module.fail_json(msg=f"Could not destroy the qdevice {stderr}", **result)

    # creating a new qdevice
    if not result["qdevice_already_created"] and state != "absent":
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)

        cmd = ["pcs", "qdevice", "setup", "model", model_name]
        rc, _, stderr = module.run_command(args=cmd)
        if rc != 0:
            module.fail_json(f"Couldn't create qdevice: {stderr}", **result)

    # set vars
    result["is_qdevice_started"] = isQdeviceStarted(model_name, module)
    result["is_qdevice_enabled"] = isQdeviceEnabled(module)

    # we dont care about the state of the qdevice
    if state == "present" or state == "absent":
        module.exit_json(**result)

    hasToBeStarted = state == "started"

    # set start and enable
    if (
        result["is_qdevice_started"] != hasToBeStarted
        or result["is_qdevice_enabled"] != enabled
    ):
        result["changed"] = True
    if module.check_mode:
        module.exit_json(**result)

    rc, stderr = setStartStatusQdevice(model_name, hasToBeStarted, module)
    if not rc and hasToBeStarted:
        module.fail_json(f"Couldn't start the qdevice, {stderr}", **result)
    elif not rc and not hasToBeStarted:
        module.fail_json(f"Couldn't stop the qdevice, {stderr}", **result)

    rc, stderr = setEnablingQdevice(model_name, enabled, module)
    if not rc and enabled:
        module.fail_json(f"Couldn't enable the qdevice, {stderr}", **result)
    elif not rc and not enabled:
        module.fail_json(f"Couldn't disable the qdevice, {stderr}", **result)

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
