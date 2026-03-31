from ansible.module_utils.basic import AnsibleModule
from ansible_collections.neteye.pcs.plugins.module_utils.cluster import isAlreadyCluster

__metaclass__ = type

DOCUMENTATION = r"""
---
module: resource

short_description: Manages pcs constraints

version_added: "1.0.0"

description: Adds constraints to pcs cluster

options:
    constraint_type:
        description: type of the constraint
        required: true
        type: str
        choices: ["colocation", "order"]
    state:
        description: whether the constraint should be present or not
        required: true
        type: str
        choices: ["present", "absent"]
    source_resource:
        description: resource id of the source resource
        required: true
        type: str
    dest_resource:
        description: resource id of the target resource
        required: true
        type: str
    source_resource_order_type:
        description: type of the order constraint
        required: false
        type: str
        choices: ["start", "stop", "promote", "demote"]
        default: start
    dest_resource_order_type:
        description: type of the order constraint
        required: false
        type: str
        choices: ["start", "stop", "promote", "demote"]
        default: start
    resource_order_action:
        description: action of the order constraint
        required: false
        type: str
        choices: ["mandatory", "optional"]
        default: mandatory
    order_symmetric:
        description: whether the order constraint is symmetric
        required: false
        type: bool
        default: true
"""

EXAMPLES = r"""
- name: Add new colocation
  neteye.pcs.constraints:
    constraint_type: colocation
    state: present
    source_resource: something
    dest_resource: somethingElse

- name: Delete colocation
  neteye.pcs.constraint:
    constraint_type: colocation
    state: absent
    source_resource: something
    dest_resource: somethingElse

- name: Order the resources
  neteye.pcs.constraint:
    constraint_type: order
    state: present
    source_resource: something
    dest_resource: somethingElse
    source_resource_order_type: start
    dest_resource_order_type: stop
    resource_order_action: mandatory
    order_symmetric: true
"""

RETURN = r"""
cluster_already_created:
    description: whether the cluster was already present
    type: bool
    returned: always
    sample: false

constraint_already_exists:
    description: whether the constraint was already present
    type: bool
    returned: always
    sample: true
"""


def run_module():
    module_args = dict(
        constraint_type=dict(
            type="str", required=True, choices=["colocation", "order"]
        ),
        state=dict(
            type="str",
            required=True,
            choices=["present", "absent"],
        ),
        source_resource=dict(type="str", required=True),
        dest_resource=dict(type="str", required=True),
        source_resource_order_type=dict(
            type="str",
            required=False,
            default="start",
            choices=["start", "stop", "promote", "demote"],
        ),
        dest_resource_order_type=dict(
            type="str",
            required=False,
            default="start",
            choices=["start", "stop", "promote", "demote"],
        ),
        resource_order_action=dict(
            type="str",
            required=False,
            default="mandatory",
            choices=["mandatory", "optional"],
        ),
        order_symmetric=dict(type="bool", required=False, default=True),
    )

    result = dict(
        changed=False,
        cluster_already_created=False,
        constraint_already_exists=False,
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    constraint_type: str = module.params["constraint_type"]
    state: str = module.params["state"]
    source_resource: str = module.params["source_resource"]
    dest_resource: str = module.params["dest_resource"]
    source_resource_order_type: str = module.params["source_resource_order_type"]
    dest_resource_order_type: str = module.params["dest_resource_order_type"]
    resource_order_action: str = module.params["resource_order_action"]
    order_symmetric: bool = bool(module.params["order_symmetric"])

    # check if a cluster is already created
    result["cluster_already_created"] = isAlreadyCluster(module)

    if not result["cluster_already_created"]:
        module.fail_json(msg="You are not in a cluster!", **result)

    # fetch the constraints
    cmd: list[str] = ["pcs", "constraint", constraint_type, "config"]
    rc, stdout, stderr = module.run_command(args=cmd)

    if rc != 0:
        module.fail_json(msg=f"Failed fatching cluster constraints, {stderr}", **result)

    # check if the constraint already exists
    if constraint_type == "colocation":
        result["constraint_already_exists"] = (
            f"{source_resource} with {dest_resource}" in stdout
        )

    elif constraint_type == "order":
        result["constraint_already_exists"] = (
            f"{source_resource_order_type} {source_resource} then {dest_resource_order_type} {dest_resource}"
            in stdout
        )

    # check if the constraint already exists that is different from the one we want to assert
    if constraint_type == "order" and result["constraint_already_exists"]:
        if order_symmetric != ("non-symmetrical" not in stdout):
            module.fail_json(
                msg="The constraint is already present but with different symmetric value",
                **result,
            )
        if f"(kind:{resource_order_action.capitalize()})" not in stdout:
            module.fail_json(
                msg="The constraint is already present but with different source resource order type",
                **result,
            )

    # delete the constraint
    if result["constraint_already_exists"] and state == "absent":
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)

        cmd: list[str] = ["pcs", "constraint", constraint_type, "remove"]
        if constraint_type == "colocation":
            cmd += [source_resource, dest_resource]
        elif constraint_type == "order":
            cmd += [
                source_resource_order_type,
                source_resource,
                "then",
                dest_resource_order_type,
                dest_resource,
            ]

        rc, _, stderr = module.run_command(args=cmd)
        if rc != 0:
            module.fail_json(msg=f"Could not remove constraint, {stderr}", **result)

    # creating the constraint
    if not result["constraint_already_exists"] and state == "present":
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)

        cmd = [
            "pcs",
            "constraint",
            constraint_type,
        ]
        if constraint_type == "colocation":
            cmd += ["add", source_resource, "with", dest_resource]
        elif constraint_type == "order":
            cmd += [
                source_resource_order_type,
                source_resource,
                "then",
                dest_resource_order_type,
                dest_resource,
                f"kind={resource_order_action.capitalize()}",
                f"symmetrical={str(order_symmetric).lower()}",
            ]
        rc, _, stderr = module.run_command(args=cmd)
        if rc != 0:
            module.fail_json(f"Couldn't add the constraint, {stderr}", **result)

    module.exit_json(**result)


def main() -> None:
    run_module()


if __name__ == "__main__":
    main()
