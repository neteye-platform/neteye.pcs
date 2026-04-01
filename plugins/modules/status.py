from ansible.module_utils.basic import AnsibleModule, missing_required_lib
from typing import Tuple
from lxml import etree

__metaclass__ = type

DOCUMENTATION = r"""
---
module: status

short_description: Parse the output of pcs status command

version_added: "1.0.0"

description: Ansible module to parse pcs status command output
"""

RETURN = r"""
resources:
    description: Returns a dictionary with the parsed output of pcs status command, grouping resources by their role
    type: dict
    returned: always
    sample: {
               "Demoting": {},
               "Migrating": {},
               "Promoted": {},
               "Promoting": {},
               "Started": {
                  "tornado_virt_ip": {
                     "active": "true",
                     "blocked": "false",
                     "failed": "false",
                     "failure_ignored": "false",
                     "group": "tornado_group",
                     "maintenance": "false",
                     "managed": "true",
                     "nodes_running_on": "1",
                     "orphaned": "false",
                     "resource_agent": "ocf::heartbeat:IPaddr2",
                     "role": "Started",
                     "running_on_nodes": [
                        "neteye-cluster1.neteyelocal"
                     ]
                  }
               },
               "Starting": {},
               "Stopped": {},
               "Stopping": {},
               "Unpromoted": {}
            }
"""


def getPcsFullXmlOutput(module: AnsibleModule) -> str:
    cmd = ["pcs", "status", "xml"]
    rc, pcs_status_output, err = module.run_command(args=cmd)
    if rc != 0:
        module.fail_json(
            msg="Command execution failed.\nCommand: `%s`\nError: %s" % (cmd, err)
        )
    return pcs_status_output


def parseResource(resource, group=None) -> Tuple[str, dict]:
    resource_dict = dict(resource.attrib)
    nodes = resource.xpath("node")
    # pcs allows a resource to run on multiple nodes, but in Neteye a resource is
    # always run on a single node. For compatibility with pcs we will return a
    # list of nodes, but the list will always contain a single element.
    # # might be undefined for stopped resources
    running_on_nodes = []
    if nodes:
        running_on_nodes = [node.get("name") for node in nodes]
    resource_dict["running_on_nodes"] = running_on_nodes
    resource_id = resource_dict.pop("id")
    resource_dict["group"] = group
    return resource_id, resource_dict


def parsePcsStatusXmlOutput(module: AnsibleModule, pcs_status_output: str) -> dict:
    try:
        tree = etree.fromstring(pcs_status_output)
    except Exception as e:
        module.fail_json(msg="Could not parse pcs xml status output: (%s)" % e)
    try:
        resources = tree.xpath("//resources/resource")
        groups = tree.xpath("//resources/group")
        # see https://github.com/ClusterLabs/pcs/blob/ce5cf6f7eba8e80f132aa9121c822a8f0d7a17f8/pcs/common/const.py#L16C1-L26C59
        out_dict = {
            "Started": {},
            "Stopped": {},
            "Promoted": {},
            "Unpromoted": {},
            "Starting": {},
            "Stopping": {},
            "Migrating": {},
            "Promoting": {},
            "Demoting": {},
        }
        for resource in resources:
            resource_id, resource_dict = parseResource(resource)
            out_dict[resource.get("role")][resource_id] = resource_dict

        for group in groups:
            group_id = group.get("id")
            for resource in group.xpath("resource"):
                resource_id, resource_dict = parseResource(resource, group_id)
                out_dict[resource.get("role")][resource_id] = resource_dict

    except Exception as e:
        module.fail_json(
            msg="Unable to process xml output from pcs status command: (%s)" % e
        )
    return out_dict


def run_module():
    module_args = dict()

    result = dict(
        changed=False,
    )

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    result["resources"] = parsePcsStatusXmlOutput(module, getPcsFullXmlOutput(module))

    module.exit_json(**result)


def main():
    run_module()


if __name__ == "__main__":
    main()
