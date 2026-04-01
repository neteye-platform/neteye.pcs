import functools
import tempfile
from time import sleep
from typing import Any, Callable, ClassVar, Dict, List, Optional, Tuple, Union

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.neteye.pcs.plugins.module_utils.cluster import isAlreadyCluster
from lxml import etree

DOCUMENTATION = r"""
---
module: resource

short_description: Creates, updates pcs resources

version_added: "1.0.0"

description: Creates and updates cluster resource using pcs

options:
    name:
        description:
          - the name of the resource
          - if '*' is specified and state == 'cleanedup', it will perform a cleanup of all resources
        required: true
        type: str
    state:
        description:
          - the desired state of the resource
          - if the resource doesn't exists, it will only be created if state is one of ['present', 'started', 'stopped']
          - if the resource is 'unmanaged' and state != 'managed' or 'unmanaged' the operation won't be performed and
            the module will fail
          - Note; idempotency issue, if state is 'cleanedup' and a wildcard is used, the result will always be changed,
            even if there was no resource to be rescued
        required: true
        type: str
        choices: ['present', 'absent', 'started', 'stopped', 'restarted', 'cleanedup', 'managed', 'unmanaged']
    resource_type:
        description: type of the resource in the following format [<standard>[<provider>]]<type>
        required: false
        type: str
    resource_options:
        description: Optional params for resource creation. This can be a single option in the form of key+value or a
                    list of options
        required: false
        type: raw
    operation_actions:
        description: Operation action. This can be a single option or a list of options.
        required: false
        type: raw
    timeout:
        description:
            - time in seconds to wait for starting/stopping/restarting the resource
            - if timeout is not specified, the default value of 2 min will be use (pcs default value is 60 min)
        required: false
        default: 240
        type: int
    group:
        description:
            - group to put the resource in
            - note that this will only be considered upon the creation of the resource
        required: false
        type: str
    check_interval:
        description: time in seconds to wait between retries for checking the resource statuses and transactions
        required: false
        default: 5
        type: int
    retry:
        description: number of retries to perform when waiting for the resource to be stable
        required: false
        default: 60
        type: int
"""

EXAMPLES = r"""
- name: Create cluster_ip resource
  neteye.pcs.resource:
    name: cluster_ip
    state: present
    resource_type: ocf:heartbeat:IPaddr2
    resource_options: [ip=10.69.69.69, cidr_netmask=24]
    operation_actions: monitor interval=30s

- name: Create my_resource resource
  neteye.pcs.resource:
    name: my_resource
    state: present
    resource_type: systemd:something
    resource_options: my_option=my_value
    operation_actions: [["monitor", "interval=30s"], ["something", "somethingElse"]]
    group: some_group

- name: Restart my_resource
  neteye.pcs.resource:
    name: my_resource
    state: restarted
    timeout: 60
    check_interval: 10

- name: Cleanup all resources
  neteye.pcs.resource:
    name: "*"
    state: cleanedup
    retry: 5

- name: Unmanage my_resource
  neteye.pcs.resource:
    name: my_resource
    state: unmanaged
"""

RETURN = r"""
resource_already_existed:
    description: whether the resource already existed
    type: bool
    returned: if name != '*'
    sample: true
resource_started:
    description: whether the resource is started or stopped
    type: bool
    returned: if name != '*' or state != cleanedup
    sample: true
cluster_already_created:
    description: whether there is a cluster
    type: bool
    returned: always
    sample: false
was_resource_managed:
    description: whether the resource was managed or unmanaged
    type: bool
    returned: always
    sample: true
was_resource_failed:
    description: whether the resource was in failed state
    type: bool
    returned: when resource_already_existed is true
    sample: false
"""

# NOTE: this variable actually set the default value for the retry and check_interval variables. If user wants to change
# the default value, it will alter the value of this variable.
retry: int = 60
check_interval: int = 5


def with_retries(retries: int) -> Callable[..., Callable[..., None]]:
    def __with_retries(func: Callable[..., None]) -> Callable[..., None]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> None:
            attempts = 0
            msg = ""
            while attempts < retries:
                attempts += 1
                try:
                    return func(*args, **kwargs)
                except (TimeoutOrRetryError, CommandFailedError) as e:
                    msg = str(e)
                    sleep(check_interval)
                    continue
            msg = f"Max retries ({retries}) reached: {msg}"
            raise TimeoutOrRetryError(msg)

        return wrapper

    return __with_retries


class ModuleRuntimeError(Exception):
    trace_msgs: ClassVar[List[str]] = []

    def __init__(self, message: str) -> None:
        ModuleRuntimeError.trace_msgs.append(
            f"neteye.pcs.resource({self.__class__}){message}\n",
        )
        super().__init__(message)


class CommandFailedError(ModuleRuntimeError):
    """A pcs command has failed."""


class PacemakerError(ModuleRuntimeError):
    """Pacemaker had an unexpected behaviour."""


class TimeoutOrRetryError(ModuleRuntimeError):
    """Timeout or retries reached."""


class InternalError(ModuleRuntimeError):
    """Some assumptions were wrong, check developer mental health."""


def get_resource_from_resources(
    resource_name: str,
    resources: etree._Element,
) -> Union[Tuple[etree._Element, Union[str, None]], None]:
    """Parse the 'resources' element returned by crm commands to get the resource object.

    Parameters
    ----------
    resource_name : str
        The name of the resource to get.
    resources : etree._Element
        The 'resources' element returned by crm commands.

    Returns
    -------
    Union[Tuple[etree._Element, Union[str, None]], None]
        The resource object and the group name if the resource is part of a group, otherwise None.

    Raises
    ------
    PacemakerError
        If the 'resources' element is missing in the output xml.

    """
    for resource in resources.findall("resource"):
        resource_id = resource.get("id")
        if resource_id is None:
            msg = f"Missing 'id' field for resource {resource_name}"
            raise PacemakerError(msg)
        if resource_id == resource_name:
            return (resource, None)

    for group in resources.findall("group"):
        for resource in group.findall("resource"):
            if resource.get("id") == resource_name:
                group_name = group.get("id")
                if group_name is None:
                    msg = f"Missing group name for grouped resource {resource_name}"
                    raise PacemakerError(msg)

                return (resource, group_name)

    return None


def get_resource(
    resource_name: str,
    module: AnsibleModule,
) -> Union[Tuple[etree._Element, Union[str, None]], None]:
    """Get the resource object from the cluster.

    Parameters
    ----------
    resource_name : str
        The name of the resource to get.
    module : AnsibleModule
        The AnsibleModule object.

    Returns
    -------
    Union[Tuple[etree._Element, Union[str, None]], None]
        The resource object and the group name if the resource is part of a group, otherwise None.

    Raises
    ------
    CommandFailedError
        If the command to get the resources fails.
    PacemakerError
        If the output xml is not valid or the 'resources' element is missing.

    """
    cmd = ["crm_resource", "--output-as=xml"]
    rc, stdout, stderr = module.run_command(args=cmd)
    if rc not in (0, 105):
        msg = f"Could not get the resources ({cmd!s}): {stderr}"
        raise CommandFailedError(msg)

    try:
        root = etree.fromstring(stdout)
    except etree.ParseError as e:
        msg = f"Could not parse the resources xml output ({cmd!s}): {e}"
        raise PacemakerError(msg) from e

    resources = root.find("resources")
    if resources is None:
        msg = f"Could not find the resources element in the output xml ({cmd!s})"
        raise PacemakerError(msg)

    return get_resource_from_resources(resource_name, resources)


def is_resource_started(resource: etree._Element) -> bool:
    """Check if the resource is started."""
    role = resource.get("role")
    active = resource.get("active")
    if role is None or active is None:
        msg = f"Missing resource fields for checking the resource Started state: role: {role}, active: {active}"
        raise PacemakerError(msg)
    return role == "Started" and active == "true"


def is_resource_stopped(resource: etree._Element) -> bool:
    """Check if the resource is stopped."""
    role = resource.get("role")
    if role is None:
        msg = f"Missing resource fields for checking the resource Stopped state: role: {role}"
        raise PacemakerError(msg)
    return role == "Stopped"


def is_resource_disabled(resource: etree._Element) -> bool:
    """Check if the resource is disabled."""
    role = resource.get("role")
    target_role = resource.get("target_role")
    if role is None:
        msg = f"Missing resource fields for checking the resource Disabled state: role: {role}"
        raise PacemakerError(msg)
    return role == "Stopped" and target_role == "Stopped"


def is_resource_managed(resource: etree._Element) -> bool:
    """Check if the resource is managed."""
    managed = resource.get("managed")
    if managed is None:
        msg = f"Missing resource fields for checking the resource Managed state: managed: {managed}"
        raise PacemakerError(msg)
    return managed == "true"


def is_resource_failed(resource_name: str, module: AnsibleModule) -> bool:
    """Check if the resource is in a failed state."""
    cmd = ["pcs", "resource", "failcount", "show", resource_name]
    rc, stdout, _ = module.run_command(args=cmd)
    if rc != 0:
        return None

    return len(stdout.split("\n")) > 2


@with_retries(retry)
def wait_for_resource_stable(
    resource_name: str,
    module: AnsibleModule,
    result: Optional[Dict[str, bool]],
) -> None:
    """Wait for the resource to be stable, by checking if there are any transactions.

    Once the resource is stable, it will fill the result dictionary with the resource status.

    Raises
    ------
    TimeoutOrRetryError
        If the resource is not stable after the timeout.

    """
    if result is None:
        result = {}
    transaction_cmd = ["crm_simulate", "--simulate", "--live-check", "--output-as=xml"]

    last_reason = ""
    rc, stdout, stderr = module.run_command(args=transaction_cmd)
    if rc != 0:
        msg = f"Could not get the resource transaction status ({transaction_cmd!s}): {stderr}"
        raise CommandFailedError(msg)

    try:
        root = etree.fromstring(stdout)
    except etree.ParseError as e:
        msg = f"Could not parse the transaction xml output ({transaction_cmd!s}): {e}"
        raise PacemakerError(msg) from e

    # check status code and message
    status = root.find("status")
    if status is None:
        msg = f"Could not find the status element in the transaction output ({transaction_cmd!s})"
        raise PacemakerError(msg)
    if status.get("code") != "0":
        msg = f"Transaction failed with code {status.get('code')}: {status.get('message')}"
        raise PacemakerError(msg)

    # get list of actions
    actions: List[etree._Element] = root.find("actions") or []
    transition: List[etree._Element] = root.find("transition") or []

    # for each action check if the resource is in a transaction
    matching_resource_actions = [
        action for action in actions if action.get("resource") == resource_name
    ]
    matching_resource_transition = [
        action for action in transition if action.get("resource") == resource_name
    ]

    if len(matching_resource_actions) == 0 and len(matching_resource_transition) == 0:
        cluster_status = root.find("cluster_status")
        if cluster_status is None:
            msg = "Could not find the cluster_status element in the transaction output"
            raise PacemakerError(msg)
        resources = cluster_status.find("resources")
        if resources is None:
            msg = "Could not find the resources element in the transaction output"
            raise PacemakerError(msg)

        resource_and_group = get_resource_from_resources(resource_name, resources)
        if resource_and_group is None:
            msg = (
                f"Could not find the resource {resource_name} in the transaction output"
            )
            raise InternalError(msg)
        resource, _ = resource_and_group

        # NOTE: This might be confusing, Started and Stopped are not always the opposite of each other, as a
        # resource can be disabled and also Starting or Stopping. It should be because we wait for the resource to
        # be stable, its a safety net (almost, no guarantees).

        # get resource started status
        result["was_resource_started"] = is_resource_started(resource)

        # get resource stopped status
        result["was_resource_stopped"] = is_resource_stopped(resource)

        # get resource disabled status
        result["was_resource_disabled"] = is_resource_disabled(resource)

        # get resource managed
        result["was_resource_managed"] = is_resource_managed(resource)

        # NOTE: Another part that could be confusing. We don't really know if the resource is in failed state in
        # some nodes but not in others. This checks if at least ONE node has the resource in a failed state.

        result["was_resource_failed"] = is_resource_failed(resource_name, module)

        # TODO: If the previous assumption weren't enough, we could insert here a check of stableness of the whole
        # group of a resource.

        # NOTE: Probably here the cluster is doing something, as the resource must never be in the following state
        # at the same time during normal operation. This is why this check is needed: to be sure that the resource
        # is not in a weird, unexpected, unknown, undesirable, invalid, unnatural, head-hurting and
        # breaking-any-assumption-and-law-of-physics state. Please don't ask me how I know this.
        if not (
            not result["was_resource_disabled"]
            and not result["was_resource_failed"]
            and result["was_resource_stopped"]
        ):
            return  # HAPPY PATH

    if len(matching_resource_actions) > 0:
        last_reason = f"reason was: {matching_resource_actions[0].get('reason')}"

    msg = "Timeout reached while waiting for resource to be stable"
    if last_reason:
        msg += f": {last_reason}"

    raise TimeoutOrRetryError(msg)


@with_retries(3)
def set_resource_state_with_retry(
    resource_name: str,
    resource_state: str,
    module: AnsibleModule,
    timeout: int,
) -> None:
    """Set the resource state with retries.

    Raises
    ------
    TimeoutOrRetryError
        If the resource state could not be set after the retries.

    """
    result: Dict[str, bool] = {}

    cmd = ["pcs", "resource"]
    if resource_state == "started":
        cmd += ["enable", resource_name]
        cmd.append(f"--wait={timeout}")

    elif resource_state == "stopped":
        cmd += ["disable", resource_name]
        cmd.append(f"--wait={timeout}")

    elif resource_state == "restarted":
        cmd += ["restart", resource_name]
        cmd.append(f"--wait={timeout}")

    elif resource_state == "cleanedup":
        cmd += ["cleanup", resource_name]

    elif resource_state == "managed":
        cmd += ["manage", resource_name]

    elif resource_state == "unmanaged":
        cmd += ["unmanage", resource_name]

    else:
        msg = f"Invalid resource state: {resource_state}"
        raise InternalError(msg)

    rc, _, stderr = module.run_command(args=cmd)

    if rc != 0:
        msg = (
            f"Could not set the resource state to {resource_state} ({cmd!s}): {stderr}"
        )
        raise CommandFailedError(msg)

    wait_for_resource_stable(resource_name, module, result)

    # NOTE: If the resource state is one that requires the resource to be up and running check if the resource is
    # started and check that it is not in a failed state right after, otherwise fail
    if resource_state in ("started", "restarted", "cleanedup"):
        if result["was_resource_failed"]:
            resource_state = "cleanedup"
        if result["was_resource_started"]:
            return  # HAPPY PATH
    elif resource_state == "stopped":
        if result["was_resource_stopped"] and result["was_resource_disabled"]:
            return  # HAPPY PATH
    else:
        return  # HAPPY PATH

    msg = f"Could not set the resource state to {resource_state}: {stderr}"
    raise TimeoutOrRetryError(msg)


def cleanup_all_resources(module: AnsibleModule) -> None:
    """Cleanup all resources in the cluster."""
    cmd = ["pcs", "resource", "cleanup"]
    rc, _, stderr = module.run_command(args=cmd)
    if rc != 0:
        msg = f"Could not cleanup all resources ({cmd!s}): {stderr}"
        raise CommandFailedError(msg)


def run_module(module: AnsibleModule, result: Dict[str, bool]) -> None:
    resource_name = str(module.params["name"])
    state = str(module.params["state"])
    resource_type = module.params["resource_type"]
    resource_options = module.params["resource_options"]
    operation_actions = module.params["operation_actions"]
    timeout = int(module.params["timeout"])
    group = module.params["group"]
    global retry  # NOQA: PLW0603
    retry = int(module.params["retry"])
    global check_interval  # NOQA: PLW0603
    check_interval = int(module.params["check_interval"])

    # parsing the parameters
    if resource_options and not isinstance(resource_options, (str, list)):
        module.fail_json(
            msg=f"Parameter 'resource_options' must be either a 'str' or a 'list', found {type(resource_options)}",
            **result,
        )

    if operation_actions and not isinstance(operation_actions, (str, list)):
        module.fail_json(
            msg=f"Parameter 'op_parameters' must be either a 'str' or a 'list', found {type(operation_actions)}",
            **result,
        )

    if timeout <= 0 or retry <= 0 or check_interval <= 0:
        module.fail_json(
            msg="Parameters 'timeout', 'retry' and 'check_interval' must be greater than 0",
            **result,
        )

    # check if a cluster is already created
    result["cluster_already_created"] = isAlreadyCluster(module)

    if not result["cluster_already_created"]:
        module.fail_json(msg="You are not in a cluster!", **result)

    # wildcard for cleanup all resources
    if resource_name == "*":
        if state != "cleanedup":
            module.fail_json(
                msg="Wildcard '*' is only available for 'cleanedup' state!",
                **result,
            )

        result["changed"] = True

        if module.check_mode:
            module.exit_json(**result)

        try:
            cleanup_all_resources(module)
        except CommandFailedError as e:
            module.fail_json(msg=e, **result)

        module.exit_json(**result)

    resource_and_group = get_resource(resource_name, module)
    # NOTE: The `virtual_check_mode` var indicates that the resource is unmanaged, we might still continue if no change
    #       is needed and return that all is good, but if some changes are needed we must fail the module
    virtual_check_mode = False
    if resource_and_group is None:
        result["resource_already_existed"] = False
    else:
        result["resource_already_existed"] = True
        resource, found_group = resource_and_group

        result["was_resource_managed"] = is_resource_managed(resource)

        if not result["was_resource_managed"] and state not in ("managed", "unmanaged"):
            virtual_check_mode = True

        # assert group is what we expect, if provided
        if group and group != found_group:
            module.fail_json(
                msg=f"Resource is not part of {group}, found {found_group}",
                **result,
            )

    # delete the resource
    if result["resource_already_existed"] and state == "absent":
        if virtual_check_mode:
            # Unmanaged resource, cannot perform operation
            module.fail_json(
                msg="Cannot perform operation on an unmanaged resource!",
                **result,
            )
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)

        cmd = ["pcs", "resource", "remove", resource_name]
        rc, _, stderr = module.run_command(args=cmd)
        if rc != 0:
            module.fail_json(msg=f"Could not delete the resource, {stderr}", **result)

        result["resource_started"] = False

    # create new resource
    if not result["resource_already_existed"] and state != "absent":
        if not resource_type:
            module.fail_json(
                msg="Cannot create a pcs resource without a resource type",
                **result,
            )

        if virtual_check_mode:
            # Unmanaged resource, cannot perform operation
            module.fail_json(
                msg="Cannot perform operation on an unmanaged resource!",
                **result,
            )
        result["changed"] = True
        if module.check_mode:
            module.exit_json(**result)

        # create the resource
        cmd = [
            "pcs",
            "resource",
            "create",
            resource_name,
            resource_type,
        ]

        if group:
            cmd += ["--group", group]

        # add resource_options to cmd, supports parameter as a string or a list
        if resource_options:
            if isinstance(resource_options, list):
                cmd += resource_options
            elif isinstance(resource_options, str):
                cmd.append(resource_options)

        # add operation_actions to cmd, supports parameter as a string, a list, or a list of lists
        if operation_actions:
            cmd.append("op")

            if isinstance(operation_actions, list) and isinstance(
                operation_actions[0],
                list,
            ):
                for op_act in operation_actions:
                    cmd += op_act
            elif isinstance(operation_actions, list) and isinstance(
                operation_actions[0],
                str,
            ):
                cmd += operation_actions
            elif isinstance(operation_actions, str):
                operation_actions = operation_actions.split(" ")
                cmd += operation_actions

        rc, _, stderr = module.run_command(args=cmd)
        if rc != 0:
            module.fail_json(
                msg=f"Error while creating the resource {stderr}",
                **result,
            )

    # we don't care about the resource state, exit
    if state in ("absent", "present"):
        module.exit_json(**result)

    # NOTE: Here we wait for the resource to be stable, as the resource can be doing something nasty while we are trying
    # to manipulate it. The following function will fillout the result dictionary with the resource status.

    try:
        wait_for_resource_stable(resource_name, module, result)
    except TimeoutOrRetryError as e:
        module.fail_json(
            msg=f"While waiting for resource to be stable an error occurred: {e!s}",
            **result,
        )

    # started and we only care that is up, exit
    if result["was_resource_started"] and state in "started":
        module.exit_json(**result)

    # no node has the resource failed so no need to cleanup, exit
    if not result["was_resource_failed"] and state == "cleanedup":
        module.exit_json(**result)

    # resource is already disabled, exit
    if result["was_resource_disabled"] and state == "stopped":
        # but we must guarantee that the resource is stopped
        if result["was_resource_started"]:
            try:
                wait_for_resource_stable(resource_name, module)
            except TimeoutOrRetryError as e:
                module.fail_json(
                    msg=f"While waiting for resource to be stopped an error occurred: {e!s}",
                    **result,
                )
        module.exit_json(**result)

    # nothing to do, exit
    if result["was_resource_managed"] and state == "managed":
        module.exit_json(**result)
    if not result["was_resource_managed"] and state == "unmanaged":
        module.exit_json(**result)

    # NOTE: if we got here, we need to change the resource state

    if virtual_check_mode:
        # Unmanaged resource, cannot perform operation
        module.fail_json(
            msg="Cannot perform operation on an unmanaged resource!",
            **result,
        )

    result["changed"] = True
    if module.check_mode:
        module.exit_json(**result)

    # "restarted" keyword may be abused by the programmer to force a new config reload for example, so we need to do
    # some extra checks about what pacemaker really needs to do
    if state == "restarted":
        # if the resource is disabled we have two possibilities:
        # it has failcounts == 0: so we can just enable it and paceamker will actually start it
        # it has failcounts > 0:  so an enable might not work because failcounts prevents the resource to be started
        #                         correctly, but `set_resource_state_with_retry` will take care of it by enabling the
        #                         resource and then cleaning it up in the second step of the retry logic because it will
        #                         find the resource is in a failed state.
        if result["was_resource_disabled"]:
            state = "started"

        # this is important! restart won't work if the resource is in a failed state on ALL nodes, but
        # "was_resource_failed" only tells us if at least one node has the resource in a failed state. If the resource
        # is not disabled, and it's stopped and with fails count, we need to cleanup the resource first since most
        # probably the resource has failcounts on all nodes without a taint on the resource
        elif result["was_resource_stopped"]:
            if result["was_resource_failed"]:
                state = "cleanedup"
            else:
                module.fail_json(
                    msg="Resource is stopped, but has no failcounts and is not disabled",
                    **result,
                )

        # if the resource has failcounts, there are only two options:
        # if the resource is not started: then aborting is our only option, as resource state in this case is unknown
        #                                 (should never happen)
        # the resource is started:        then we can just restart it, it will remain in failed state but it will be
        #                                 cleaned up in the second step of the retry logic
        elif result["was_resource_failed"] and not result["was_resource_started"]:
            module.fail_json(
                msg="Resource is in a failed state, but is not started nor stopped",
                **result,
            )

    try:
        # Pray
        set_resource_state_with_retry(resource_name, state, module, timeout)
    except TimeoutOrRetryError as e:
        module.fail_json(
            msg=f"While setting the resource state, an error occurred: {e!s}",
            **result,
        )

    result["resource_started"] = state != "stopped"

    module.exit_json(**result)


def main() -> None:
    module_args = {
        "name": {"type": "str", "required": True},
        "state": {
            "type": "str",
            "required": True,
            "choices": [
                "present",
                "absent",
                "started",
                "stopped",
                "restarted",
                "cleanedup",
                "managed",
                "unmanaged",
            ],
        },
        "resource_type": {"type": "str", "required": False},
        "resource_options": {"type": "raw", "required": False},
        "operation_actions": {"type": "raw", "required": False},
        "timeout": {"type": "int", "required": False, "default": 240},
        "group": {"type": "str", "required": False},
        "managed": {"type": "raw", "required": False},
        "check_interval": {"type": "int", "required": False, "default": check_interval},
        "retry": {"type": "int", "required": False, "default": retry},
    }

    result: Dict[str, bool] = {
        "changed": False,
        "cluster_already_created": False,
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    try:
        run_module(module, result)
    except ModuleRuntimeError as e:
        file_path = None
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("".join(ModuleRuntimeError.trace_msgs))
            file_path = f.name

        module.fail_json(
            msg=f"During the runtime of the module, an unhandled error occurred: {e!s}\n\
            Traceback can be found in {file_path!s}",
            **result,
        )


if __name__ == "__main__":
    main()
