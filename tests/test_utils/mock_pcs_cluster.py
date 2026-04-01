from enum import Enum
from pathlib import Path
from typing import ClassVar, List, Optional, Tuple, Union

from lxml import etree

FAILED_RC = (1, "", "")
SUCCEED_RC = (0, "", "")
RETURN_TYPE = Union[None, Tuple[int, str, str]]


class MockPcsCluster:
    cluster = dict()
    cluster["enabled"] = False
    cluster["present"] = False
    cluster["recreated"] = False
    cluster["started"] = False
    cluster["authedNodes"] = []
    cluster["name"] = ""
    cluster["password"] = ""

    qdevice = dict()
    qdevice["enabled"] = False
    qdevice["present"] = False
    qdevice["started"] = False
    qdevice["algorithm"] = ""
    qdevice["host"] = ""
    qdevice["model"] = "net"

    class Resource:
        class State(Enum):
            STARTED = "Started"
            STARTING = "Starting"
            STOPPING = "Stopping"
            DISABLED = "Disabled"
            FAILED_ALL = "FailedAll"
            FAILED_PARTIAL = "FailedPartial"

        state: State
        op: ClassVar[List[str]] = []
        options: ClassVar[List[str]] = []
        group: Optional[str] = None
        name: str
        res_type: str = "ofc::neteye::dummy"
        managed: bool = True

        # testing variables:
        state_applies: ClassVar[List[Tuple[str, Optional[int]]]] = []
        in_transition: bool = False
        in_action: bool = False

        def __init__(self, name: str, state: State, **kwargs) -> None:
            self.name = name
            self.state = state
            if "group" in kwargs:
                self.group = kwargs["group"]
            if "res_type" in kwargs:
                self.res_type = kwargs["res_type"]
            if "op" in kwargs:
                self.op = kwargs["op"]
            if "options" in kwargs:
                self.options = kwargs["options"]
            if "managed" in kwargs:
                self.managed = kwargs["managed"]
            if "in_transition" in kwargs:
                self.in_transition = kwargs["in_transition"]
            if "in_action" in kwargs:
                self.in_action = kwargs["in_action"]

        def to_resource_xml(self) -> etree._Element:
            res = etree.Element("resource")
            res.set("id", self.name)
            res.set("resource_agent", self.res_type)
            res.set("managed", "true" if self.managed else "false")

            if self.state == MockPcsCluster.Resource.State.STARTED:
                res.set("role", "Started")
                res.set("active", "true")
            elif self.state == MockPcsCluster.Resource.State.STARTING:
                res.set("role", "Starting")
                res.set("active", "true")
            elif self.state == MockPcsCluster.Resource.State.STOPPING:
                res.set("role", "Stopping")
                res.set("active", "true")
                res.set("target_role", "Stopped")
            elif self.state == MockPcsCluster.Resource.State.DISABLED:
                res.set("role", "Stopped")
                res.set("active", "false")
                res.set("target_role", "Stopped")
            elif self.state == MockPcsCluster.Resource.State.FAILED_ALL:
                res.set("role", "Stopped")
                res.set("active", "false")
            elif self.state == MockPcsCluster.Resource.State.FAILED_PARTIAL:
                res.set("role", "Started")
                res.set("active", "true")
            return res

        def to_action_xml(self) -> Union[etree._Element, None]:
            """Generate xml element for resource if present in a transaction."""
            if not self.in_action:
                return None

            resource_action = etree.Element("rsc_action")
            resource_action.set("resource", self.name)
            resource_action.set("reason", "whatta is the clustah dooin")
            return resource_action

        def to_transition_xml(self) -> Union[etree._Element, None]:
            """Generate xml element for resource if present in a transaction."""
            if not self.in_transition:
                return None

            resource_transition = etree.Element("rsc_action")
            resource_transition.set("resource", self.name)
            return resource_transition

    resources: ClassVar[List[Resource]] = []
    cleanup_all_resources_count: int = 0

    class OrderingConstraint:
        class OrderType(Enum):
            START = "start"
            STOP = "stop"
            PROMOTE = "promote"
            DEMOTE = "demote"

        class ResourceOrderAction(Enum):
            OPTIONAL = "Optional"
            MANDATORY = "Mandatory"

        source_resource: str
        dest_resource: str
        source_resource_order_type: OrderType
        dest_resource_order_type: OrderType
        order_symmetric: bool = False
        resource_order_action: ResourceOrderAction = ResourceOrderAction.MANDATORY

        def __init__(
            self,
            source_resource: str,
            dest_resource: str,
            source_resource_order_type: OrderType,
            dest_resource_order_type: OrderType,
            order_symmetric: Optional[bool] = None,
            resource_order_action: Optional[ResourceOrderAction] = None,
        ) -> None:
            self.source_resource = source_resource
            self.dest_resource = dest_resource
            self.source_resource_order_type = source_resource_order_type
            self.dest_resource_order_type = dest_resource_order_type
            if order_symmetric:
                self.order_symmetric = order_symmetric
            if resource_order_action:
                self.resource_order_action = resource_order_action

    class ColocationConstraint:
        source_resource: str
        dest_resource: str
        score: str = "INFINITY"

        def __init__(self, source_resource: str, dest_resource: str) -> None:
            self.source_resource = source_resource
            self.dest_resource = dest_resource

    constraints: ClassVar[List[Union[OrderingConstraint, ColocationConstraint]]] = []

    @staticmethod
    def create_resources_xml() -> etree._Element:
        resources = etree.Element("resources")

        for resource in MockPcsCluster.resources:
            res_element = resource.to_resource_xml()

            parent = resources
            # if resource has group create one #NOTE: in this case multiple resources inside same group is not supported
            if resource.group:
                group = etree.Element("group")
                group.set("id", resource.group)
                resources.append(group)
                parent = group

            parent.append(res_element)
        return resources

    @staticmethod
    def get_resource_by_name(resource_name: str) -> Optional[Resource]:
        resources = [r for r in MockPcsCluster.resources if r.name == resource_name]
        if resources:
            return resources[0]
        return None

    @staticmethod
    def pcs_resource_failcount_show(args: List[str]) -> RETURN_TYPE:
        # get resource failcount
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        resource_name = args[-1]

        resource = MockPcsCluster.get_resource_by_name(resource_name)
        if not resource:
            return FAILED_RC

        if resource.state in (
            MockPcsCluster.Resource.State.FAILED_ALL,
            MockPcsCluster.Resource.State.FAILED_PARTIAL,
        ):
            return (0, "".join("here to waste some lines\n" * 4), "")

        return (0, f"No failscount found for resource'{resource_name}'\n", "")

    @staticmethod
    def crm_resource(args: List[str]) -> RETURN_TYPE:
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        if args[1] != "--output-as=xml":
            return (1, "", "Missing required args")

        root = etree.Element("pacemaker-result")
        status = etree.Element("status")
        if len(MockPcsCluster.resources) != 0:
            status.set("code", "0")
            status.set("message", "OK")
        else:
            status.set("code", "105")
            status.set("message", "No such object")
            root.append(etree.Element("resources"))
            return (105, etree.tostring(root).decode(), "")
        root.append(status)
        root.append(MockPcsCluster.create_resources_xml())

        return (0, etree.tostring(root).decode(), "")

    @staticmethod
    def crm_simulate(args: List[str]) -> RETURN_TYPE:
        # get cluster transition status
        if any(
            x not in args for x in ["--simulate", "--live-check", "--output-as=xml"]
        ):
            return (1, "", "Missing required args")

        if not MockPcsCluster.cluster["present"]:
            return (1, "", "Cluster is not present")

        # generate xml for the simulation command
        root = etree.Element("pacemaker-result")
        status = etree.Element("status")
        status.set("code", "0")
        status.set("message", "OK")
        root.append(status)

        # get cluster status
        cluster_status = etree.Element("cluster_status")
        cluster_status.append(MockPcsCluster.create_resources_xml())
        root.append(cluster_status)

        actions = etree.Element("actions")
        root.append(actions)
        transitions = etree.Element("transitions")
        root.append(transitions)

        # set cluster actions and transitions
        for resource in MockPcsCluster.resources:
            action = resource.to_action_xml()
            if action:
                actions.append(action)

            transition = resource.to_transition_xml()
            if transition:
                transitions.append(transition)

        return (0, etree.tostring(root).decode(), "")

    @staticmethod
    def pcs_cluster_config(_: List[str]) -> RETURN_TYPE:
        # cluster exists
        if MockPcsCluster.cluster["present"]:
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_cluster_disable(_: List[str]) -> RETURN_TYPE:
        # cluster disabling
        if MockPcsCluster.cluster["present"]:
            MockPcsCluster.cluster["enabled"] = False
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_cluster_enable(_: List[str]) -> RETURN_TYPE:
        # cluster enabling
        # NOTE: this does not check if cluster is already enabled, this is intended
        # check the module source code for the complete NOTE
        if MockPcsCluster.cluster["present"] and MockPcsCluster.cluster["started"]:
            MockPcsCluster.cluster["enabled"] = True
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_cluster_setup(args: List[str]) -> RETURN_TYPE:
        if MockPcsCluster.cluster["present"]:
            if args[3] != "--force":
                return FAILED_RC
            MockPcsCluster.cluster["recreated"] = True
        start_index = 5 if args[3] == "--force" else 4
        # check if all nodes are authed
        if set(MockPcsCluster.cluster["authedNodes"]) != set(args[start_index::]):
            return FAILED_RC
        MockPcsCluster.cluster["present"] = True
        return SUCCEED_RC

    @staticmethod
    def pcs_cluster_start(_: List[str]) -> RETURN_TYPE:
        # start cluster
        if MockPcsCluster.cluster["present"] and not MockPcsCluster.cluster["started"]:
            MockPcsCluster.cluster["started"] = True
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_cluster_status(_: List[str]) -> RETURN_TYPE:
        # cluster is started
        if MockPcsCluster.cluster["present"] and MockPcsCluster.cluster["started"]:
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_constraint_colocation_add(args: List[str]) -> RETURN_TYPE:
        # add colocation constraint
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC
        source_resource = str(args[-3])
        dest_resource = args[-1]

        if source_resource == dest_resource:
            return FAILED_RC

        # check if resources exist
        if not any(r.name == source_resource for r in MockPcsCluster.resources):
            return FAILED_RC

        if not any(r.name == dest_resource for r in MockPcsCluster.resources):
            return FAILED_RC

        # check if constraint already exists
        if any(
            r.source_resource == source_resource and r.dest_resource == dest_resource
            for r in MockPcsCluster.constraints
            if isinstance(r, MockPcsCluster.ColocationConstraint)
        ):
            return FAILED_RC

        # NOTE: this does not check if the reverse constraint exists

        MockPcsCluster.constraints.append(
            MockPcsCluster.ColocationConstraint(source_resource, dest_resource)
        )

        return SUCCEED_RC

    @staticmethod
    def pcs_constraint_colocation_config(_: List[str]) -> RETURN_TYPE:
        # check constraint status
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        stdout = "Colocation Constraints:\n"

        for constraint in MockPcsCluster.constraints:
            if isinstance(constraint, MockPcsCluster.ColocationConstraint):
                stdout += f"  {constraint.source_resource} with {constraint.dest_resource} (score:{constraint.score})\n"

        return (0, stdout, "")

    @staticmethod
    def pcs_constraint_colocation_remove(args: List[str]) -> RETURN_TYPE:
        # remove colocation constraint
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        source_resource = args[-2]
        dest_resource = args[-1]

        for constraint in MockPcsCluster.constraints:
            if (
                isinstance(constraint, MockPcsCluster.ColocationConstraint)
                and constraint.source_resource == source_resource
                and constraint.dest_resource == dest_resource
            ):
                MockPcsCluster.constraints.remove(constraint)
                return SUCCEED_RC

        return FAILED_RC

    @staticmethod
    def pcs_constraint_order_config(_: List[str]) -> RETURN_TYPE:
        # check constraint status
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        stdout = "Ordering Constraints:\n"
        for constraint in MockPcsCluster.constraints:
            if isinstance(constraint, MockPcsCluster.OrderingConstraint):
                stdout += f"  {constraint.source_resource_order_type.value.lower()} {constraint.source_resource}"
                stdout += " then"
                stdout += f" {constraint.dest_resource_order_type.value.lower()} {constraint.dest_resource}"
                stdout += (
                    f" (kind:{constraint.resource_order_action.value.capitalize()})"
                )
                stdout += (
                    f"{' (non-symmetrical)' if not constraint.order_symmetric else ''}"
                )
                stdout += "\n"
        return (0, stdout, "")

    @staticmethod
    def pcs_constraint_order_remove(args: List[str]) -> RETURN_TYPE:
        if not MockPcsCluster.cluster["present"] or args[6] != "then":
            return FAILED_RC

        source_order_type = args[4]
        source_resource = args[5]
        dest_resource_order_type = args[7]
        dest_resource = args[8]

        for constraint in MockPcsCluster.constraints:
            if (
                isinstance(constraint, MockPcsCluster.OrderingConstraint)
                and constraint.source_resource_order_type.value == source_order_type
                and constraint.source_resource == source_resource
                and constraint.dest_resource_order_type.value
                == dest_resource_order_type
                and constraint.dest_resource == dest_resource
            ):
                MockPcsCluster.constraints.remove(constraint)
                return SUCCEED_RC

        return FAILED_RC

    @staticmethod
    def pcs_constraint_order(args: List[str]) -> RETURN_TYPE:
        # adds new order constraint
        if not MockPcsCluster.cluster["present"] or args[5] != "then":
            return FAILED_RC

        source_order_type = args[3]
        source_resource = args[4]
        dest_order_type = args[6]
        dest_resource = args[7]
        kind = args[8].replace("kind=", "") if args[8] else "Mandatory"
        symmetrical = args[9].replace("symmetrical=", "") if args[9] else "true"

        if source_order_type.lower() not in [
            name.lower()
            for name, _ in MockPcsCluster.OrderingConstraint.OrderType.__members__.items()
        ]:
            return FAILED_RC

        if dest_order_type.lower() not in [
            name.lower()
            for name, _ in MockPcsCluster.OrderingConstraint.OrderType.__members__.items()
        ]:
            return FAILED_RC

        if all(x.name != source_resource for x in MockPcsCluster.resources):
            return FAILED_RC

        if all(x.name != dest_resource for x in MockPcsCluster.resources):
            return FAILED_RC

        MockPcsCluster.constraints.append(
            MockPcsCluster.OrderingConstraint(
                source_resource,
                dest_resource,
                MockPcsCluster.OrderingConstraint.OrderType(source_order_type),
                MockPcsCluster.OrderingConstraint.OrderType(dest_order_type),
                symmetrical == "true",
                MockPcsCluster.OrderingConstraint.ResourceOrderAction(kind),
            ),
        )
        return SUCCEED_RC

    @staticmethod
    def pcs_host_auth(args: List[str]) -> RETURN_TYPE:
        node_name = args[3]
        password = args[-1]
        if password != MockPcsCluster.cluster["password"]:
            return FAILED_RC
        MockPcsCluster.cluster["authedNodes"].append(node_name)
        return SUCCEED_RC

    @staticmethod
    def pcs_pcsd_status(args: List[str]) -> RETURN_TYPE:
        # check if node is authed
        node_hostname = args[-1]
        if node_hostname in MockPcsCluster.cluster["authedNodes"]:
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_qdevice_destroy(args: List[str]) -> RETURN_TYPE:
        # destroy qdevice
        if (
            MockPcsCluster.qdevice["present"]
            and args[-1] == MockPcsCluster.qdevice["model"]
        ):
            MockPcsCluster.qdevice["present"] = False
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_qdevice_disable(args: List[str]) -> RETURN_TYPE:
        # disable qdevice
        if (
            MockPcsCluster.qdevice["present"]
            and args[-1] == MockPcsCluster.qdevice["model"]
        ):
            MockPcsCluster.qdevice["enabled"] = False
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_qdevice_enable(args: List[str]) -> RETURN_TYPE:
        # enable qdevice
        if (
            MockPcsCluster.qdevice["present"]
            and args[-1] == MockPcsCluster.qdevice["model"]
        ):
            MockPcsCluster.qdevice["enabled"] = True
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_qdevice_setup_model(args: List[str]) -> RETURN_TYPE:
        # setup qdevice
        if (
            not MockPcsCluster.qdevice["present"]
            and args[-1] == MockPcsCluster.qdevice["model"]
        ):
            MockPcsCluster.qdevice["present"] = True
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_qdevice_start(args: List[str]) -> RETURN_TYPE:
        # start qdevice
        if (
            MockPcsCluster.qdevice["present"]
            and args[-1] == MockPcsCluster.qdevice["model"]
        ):
            MockPcsCluster.qdevice["started"] = True
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_qdevice_status(args: List[str]) -> RETURN_TYPE:
        # check if qdevice is started
        if (
            MockPcsCluster.qdevice["present"]
            and MockPcsCluster.qdevice["started"]
            and args[-1] == MockPcsCluster.qdevice["model"]
        ):
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_qdevice_stop(args: List[str]) -> RETURN_TYPE:
        # stop qdevice
        if (
            MockPcsCluster.qdevice["present"]
            and args[-1] == MockPcsCluster.qdevice["model"]
        ):
            MockPcsCluster.qdevice["started"] = False
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_quorum_device_add_model(args: List[str]) -> RETURN_TYPE:
        # create new qdevice
        if MockPcsCluster.qdevice["present"]:
            return FAILED_RC
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["model"] = args[5]
        MockPcsCluster.qdevice["host"] = args[-2].split("=")[-1]
        MockPcsCluster.qdevice["algorithm"] = args[-1].split("=")[-1]
        return SUCCEED_RC

    @staticmethod
    def pcs_quorum_device_remove(_: List[str]) -> RETURN_TYPE:
        # destroy qdevice
        if MockPcsCluster.qdevice["present"]:
            MockPcsCluster.qdevice["present"] = False
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_quorum_device_status(_: List[str]) -> RETURN_TYPE:
        # check qdevice status
        if MockPcsCluster.qdevice["present"]:
            return SUCCEED_RC
        return FAILED_RC

    @staticmethod
    def pcs_resource_cleanup(args: List[str]) -> RETURN_TYPE:
        # cleanup resource
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        if len(args) == 3:
            MockPcsCluster.cleanup_all_resources_count += 1
            return SUCCEED_RC

        resource_name = args[-1]

        resource = MockPcsCluster.get_resource_by_name(resource_name)
        if not resource:
            return FAILED_RC

        resource.state = MockPcsCluster.Resource.State.STARTED
        resource.state_applies.append(("cleanup", None))

        return SUCCEED_RC

    @staticmethod
    def pcs_resource_create(args: List[str]) -> RETURN_TYPE:
        # create resource
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        resource_name = args[3]

        resource = MockPcsCluster.get_resource_by_name(resource_name)
        if resource:
            return FAILED_RC

        resource_type = args[4]

        args = args[5:]
        resource_group = None
        if "--group" in args:
            resource_group = args[1]
            args = args[2:]

        resource_op = []
        if "op" in args:
            op_index = args.index("op") + 1
            resource_op = args[op_index:]
            op_index -= 1
            args = args[:op_index]

        resource_options = args

        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                resource_name,
                MockPcsCluster.Resource.State.STARTED,
                group=resource_group,
                res_type=resource_type,
                op=resource_op,
                options=resource_options,
            ),
        )

        return SUCCEED_RC

    @staticmethod
    def pcs_resource_disable(args: List[str]) -> RETURN_TYPE:
        # stop resource
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC
        resource_name = args[3]

        if args[4] and not args[4].startswith("--wait="):
            return FAILED_RC

        wait_time = int(args[4].split("=")[-1])

        resource = MockPcsCluster.get_resource_by_name(resource_name)
        if not resource:
            return FAILED_RC

        resource.state = MockPcsCluster.Resource.State.DISABLED
        resource.state_applies.append(("disable", wait_time))

        return SUCCEED_RC

    @staticmethod
    def pcs_resource_enable(args: List[str]) -> RETURN_TYPE:
        # start resource
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        resource_name = args[3]
        if args[4] and not args[4].startswith("--wait="):
            return FAILED_RC

        wait_time = int(args[4].split("=")[-1])

        resource = MockPcsCluster.get_resource_by_name(resource_name)
        if not resource:
            return FAILED_RC

        resource.state = MockPcsCluster.Resource.State.STARTED
        resource.state_applies.append(("enable", wait_time))

        return SUCCEED_RC

    @staticmethod
    def pcs_resource_manage(args: List[str]) -> RETURN_TYPE:
        # manage resource
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        resource_name = args[-1]

        resource = MockPcsCluster.get_resource_by_name(resource_name)
        if not resource:
            return FAILED_RC

        resource.managed = True
        resource.state_applies.append(("manage", None))
        return SUCCEED_RC

    @staticmethod
    def pcs_resource_remove(args: List[str]) -> RETURN_TYPE:
        # delete resource
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        resource_name = args[-1]

        resource = MockPcsCluster.get_resource_by_name(resource_name)
        if not resource:
            return FAILED_RC

        MockPcsCluster.resources.remove(resource)
        return SUCCEED_RC

    @staticmethod
    def pcs_resource_restart(args: List[str]) -> RETURN_TYPE:
        # restart resource
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        resource_name = args[3]

        if args[4] and not args[4].startswith("--wait="):
            return FAILED_RC

        wait_time = int(args[4].split("=")[-1])

        resource = MockPcsCluster.get_resource_by_name(resource_name)
        if not resource:
            return FAILED_RC

        if resource.state in (
            MockPcsCluster.Resource.State.DISABLED,
            MockPcsCluster.Resource.State.FAILED_ALL,
            MockPcsCluster.Resource.State.STARTING,
            MockPcsCluster.Resource.State.STOPPING,
        ):
            return FAILED_RC

        resource.state_applies.append(("restart", wait_time))
        return SUCCEED_RC

    @staticmethod
    def pcs_resource_unmanage(args: List[str]) -> RETURN_TYPE:
        # unmanage resource
        if not MockPcsCluster.cluster["present"]:
            return FAILED_RC

        resource_name = args[-1]

        resource = MockPcsCluster.get_resource_by_name(resource_name)
        if not resource:
            return FAILED_RC

        resource.managed = False
        resource.state_applies.append(("unmanage", None))
        return SUCCEED_RC

    @staticmethod
    def pcs_status_xml(_: List[str]) -> RETURN_TYPE:
        cluster_health_xml_path = (
            Path(__file__).parent / "fixtures/pcs_status/healthy_cluster.xml"
        )

        with cluster_health_xml_path.open("r") as f:
            return (0, f.read(), "")

    @staticmethod
    def crm(args: List[str], cmd: str) -> RETURN_TYPE:
        # get resource status
        if cmd.startswith("crm_resource"):
            return MockPcsCluster.crm_resource(args)

        # get cluster transition status
        if cmd.startswith("crm_simulate"):
            return MockPcsCluster.crm_simulate(args)

        raise ValueError("Unknown command: " + cmd)

    @staticmethod
    def pcs(args: List[str], cmd: str) -> RETURN_TYPE:
        # cluster exists
        if cmd.startswith("pcs cluster config"):
            return MockPcsCluster.pcs_cluster_config(args)

        # cluster disabling
        if cmd.startswith("pcs cluster disable"):
            return MockPcsCluster.pcs_cluster_disable(args)

        # cluster enabling
        if cmd.startswith("pcs cluster enable"):
            return MockPcsCluster.pcs_cluster_enable(args)

        # setup new cluster
        if cmd.startswith("pcs cluster setup"):
            return MockPcsCluster.pcs_cluster_setup(args)

        # cluster is started
        if cmd.startswith("pcs cluster status"):
            return MockPcsCluster.pcs_cluster_status(args)

        # start cluster
        if cmd.startswith("pcs cluster start"):
            return MockPcsCluster.pcs_cluster_start(args)

        # add colocation constraint
        if cmd.startswith("pcs constraint colocation add"):
            return MockPcsCluster.pcs_constraint_colocation_add(args)

        # check colocation config
        if cmd.startswith("pcs constraint colocation config"):
            return MockPcsCluster.pcs_constraint_colocation_config(args)

        # remove colocation constraint
        if cmd.startswith("pcs constraint colocation remove"):
            return MockPcsCluster.pcs_constraint_colocation_remove(args)

        # check order config
        if cmd.startswith("pcs constraint order config"):
            return MockPcsCluster.pcs_constraint_order_config(args)

        # remove order constraint
        if cmd.startswith("pcs constraint order remove"):
            return MockPcsCluster.pcs_constraint_order_remove(args)

        # add order constraint
        if cmd.startswith("pcs constraint order"):
            return MockPcsCluster.pcs_constraint_order(args)

        # auth a node
        if cmd.startswith("pcs host auth"):
            return MockPcsCluster.pcs_host_auth(args)

        # check if node is authed
        if cmd.startswith("pcs pcsd status"):
            return MockPcsCluster.pcs_pcsd_status(args)

        # destroy qdevice
        if cmd.startswith("pcs qdevice destroy"):
            return MockPcsCluster.pcs_qdevice_destroy(args)

        # disable qdevice
        if cmd.startswith("pcs qdevice disable"):
            return MockPcsCluster.pcs_qdevice_disable(args)

        # enable qdevice
        if cmd.startswith("pcs qdevice enable"):
            return MockPcsCluster.pcs_qdevice_enable(args)

        # setup qdevice
        if cmd.startswith("pcs qdevice setup model"):
            return MockPcsCluster.pcs_qdevice_setup_model(args)

        # start qdevice
        if cmd.startswith("pcs qdevice start"):
            return MockPcsCluster.pcs_qdevice_start(args)

        # check if qdevice is started
        if cmd.startswith("pcs qdevice status"):
            return MockPcsCluster.pcs_qdevice_status(args)

        # stop qdevice
        if cmd.startswith("pcs qdevice stop"):
            return MockPcsCluster.pcs_qdevice_stop(args)

        # create new qdevice
        if cmd.startswith("pcs quorum device add model"):
            return MockPcsCluster.pcs_quorum_device_add_model(args)

        # destroy qdevice
        if cmd.startswith("pcs quorum device remove"):
            return MockPcsCluster.pcs_quorum_device_remove(args)

        # check qdevice status
        if cmd.startswith("pcs quorum device status"):
            return MockPcsCluster.pcs_quorum_device_status(args)

        # cleaneup resource
        if cmd.startswith("pcs resource cleanup"):
            return MockPcsCluster.pcs_resource_cleanup(args)

        # create resource
        if cmd.startswith("pcs resource create"):
            return MockPcsCluster.pcs_resource_create(args)

        # stop resource
        if cmd.startswith("pcs resource disable"):
            return MockPcsCluster.pcs_resource_disable(args)

        # start resource
        if cmd.startswith("pcs resource enable"):
            return MockPcsCluster.pcs_resource_enable(args)

        # get resource failcount
        if cmd.startswith("pcs resource failcount show"):
            return MockPcsCluster.pcs_resource_failcount_show(args)

        # manage resource
        if cmd.startswith("pcs resource manage"):
            return MockPcsCluster.pcs_resource_manage(args)

        # delete resource
        if cmd.startswith("pcs resource remove"):
            return MockPcsCluster.pcs_resource_remove(args)

        # restart resource
        if cmd.startswith("pcs resource restart"):
            return MockPcsCluster.pcs_resource_restart(args)

        # unmanage resource
        if cmd.startswith("pcs resource unmanage"):
            return MockPcsCluster.pcs_resource_unmanage(args)

        # check status
        if cmd.startswith("pcs status xml"):
            return MockPcsCluster.pcs_status_xml(args)

        raise ValueError("Unknown command: " + cmd)
