import unittest

from ansible_collections.neteye.pcs.plugins.modules import constraint
from ansible_collections.neteye.pcs.tests.test_utils.mock_ansible import (
    AnsibleExitJson,
    AnsibleFailJson,
    patchAnsibleModule,
    set_module_args,
)
from ansible_collections.neteye.pcs.tests.test_utils.mock_cluster_utils import (
    patchClusterUtils,
)
from ansible_collections.neteye.pcs.tests.test_utils.mock_pcs_cluster import (
    MockPcsCluster,
)


class TestConstraints(unittest.TestCase):
    def setUp(self) -> None:
        self.patches = [
            patchAnsibleModule(),
            patchClusterUtils(),
        ]

        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_fail_when_required_args_missing(self) -> None:
        set_module_args({})
        with self.assertRaises(AnsibleFailJson):
            constraint.main()

    def test_succeed_when_creating_colocation_constraint(self) -> None:
        MockPcsCluster.cluster["present"] = True
        source_resource = "my_resource"
        dest_resource = "awesome_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                source_resource, MockPcsCluster.Resource.State.STARTED
            )
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                dest_resource, MockPcsCluster.Resource.State.STARTED
            )
        )

        set_module_args(
            {
                "constraint_type": "colocation",
                "state": "present",
                "source_resource": source_resource,
                "dest_resource": dest_resource,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            constraint.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.constraints) == 1)

        con = next(
            c
            for c in MockPcsCluster.constraints
            if isinstance(c, MockPcsCluster.ColocationConstraint)
            and c.source_resource == source_resource
            and c.dest_resource == dest_resource
        )
        self.assertTrue(con is not None)

    def test_succeed_when_removing_colocation_constraint(self) -> None:
        MockPcsCluster.cluster["present"] = True
        source_resource = "my_resource"
        dest_resource = "awesome_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                source_resource, MockPcsCluster.Resource.State.STARTED
            )
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                dest_resource, MockPcsCluster.Resource.State.STARTED
            )
        )

        MockPcsCluster.constraints.append(
            MockPcsCluster.ColocationConstraint(source_resource, dest_resource)
        )

        set_module_args(
            {
                "constraint_type": "colocation",
                "state": "absent",
                "source_resource": source_resource,
                "dest_resource": dest_resource,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            constraint.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.constraints) == 0)

    def test_no_change_when_colocation_constrain_exists(self) -> None:
        MockPcsCluster.cluster["present"] = True
        source_resource = "my_resource"
        dest_resource = "awesome_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                source_resource, MockPcsCluster.Resource.State.STARTED
            )
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                dest_resource, MockPcsCluster.Resource.State.STARTED
            )
        )

        MockPcsCluster.constraints.append(
            MockPcsCluster.ColocationConstraint(source_resource, dest_resource)
        )

        set_module_args(
            {
                "constraint_type": "colocation",
                "state": "present",
                "source_resource": source_resource,
                "dest_resource": dest_resource,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            constraint.main()

        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.constraints) == 1)
        con = next(
            c
            for c in MockPcsCluster.constraints
            if isinstance(c, MockPcsCluster.ColocationConstraint)
            and c.source_resource == source_resource
            and c.dest_resource == dest_resource
        )
        self.assertTrue(con is not None)

    def test_no_change_when_colocation_constrain_not_exists(self) -> None:
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "constraint_type": "colocation",
                "state": "absent",
                "source_resource": "something",
                "dest_resource": "testtesttest",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            constraint.main()

        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.constraints) == 0)

    def test_succeed_when_creating_order_constraint(self) -> None:
        MockPcsCluster.cluster["present"] = True
        source_resource = "my_resource"
        dest_resource = "awesome_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                source_resource, MockPcsCluster.Resource.State.STARTED
            )
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                dest_resource, MockPcsCluster.Resource.State.STARTED
            )
        )

        set_module_args(
            {
                "constraint_type": "order",
                "state": "present",
                "source_resource": source_resource,
                "dest_resource": dest_resource,
                "source_resource_order_type": "start",
                "dest_resource_order_type": "stop",
                "resource_order_action": "mandatory",
                "order_symmetric": False,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            constraint.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.constraints) == 1)
        con = next(
            c
            for c in MockPcsCluster.constraints
            if isinstance(c, MockPcsCluster.OrderingConstraint)
            and c.source_resource == source_resource
            and c.dest_resource == dest_resource
        )

        self.assertTrue(
            con.source_resource_order_type
            == MockPcsCluster.OrderingConstraint.OrderType.START
        )
        self.assertTrue(
            con.dest_resource_order_type
            == MockPcsCluster.OrderingConstraint.OrderType.STOP
        )
        self.assertTrue(
            con.resource_order_action
            == MockPcsCluster.OrderingConstraint.ResourceOrderAction.MANDATORY
        )
        self.assertTrue(not con.order_symmetric)

    def test_succeed_when_creating_order_constraint_2(self) -> None:
        MockPcsCluster.cluster["present"] = True
        source_resource = "my_resource"
        dest_resource = "awesome_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                source_resource, MockPcsCluster.Resource.State.STARTED
            )
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                dest_resource, MockPcsCluster.Resource.State.STARTED
            )
        )

        set_module_args(
            {
                "constraint_type": "order",
                "state": "present",
                "source_resource": source_resource,
                "dest_resource": dest_resource,
                "source_resource_order_type": "demote",
                "dest_resource_order_type": "start",
                "resource_order_action": "optional",
                "order_symmetric": True,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            constraint.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.constraints) == 1)
        con = next(
            c
            for c in MockPcsCluster.constraints
            if isinstance(c, MockPcsCluster.OrderingConstraint)
            and c.source_resource == source_resource
            and c.dest_resource == dest_resource
        )

        self.assertTrue(
            con.source_resource_order_type
            == MockPcsCluster.OrderingConstraint.OrderType.DEMOTE
        )
        self.assertTrue(
            con.dest_resource_order_type
            == MockPcsCluster.OrderingConstraint.OrderType.START
        )
        self.assertTrue(
            con.resource_order_action
            == MockPcsCluster.OrderingConstraint.ResourceOrderAction.OPTIONAL
        )
        self.assertTrue(con.order_symmetric)

    def test_succeed_when_removing_order_constraint(self) -> None:
        MockPcsCluster.cluster["present"] = True
        source_resource = "my_resource"
        dest_resource = "awesome_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                source_resource, MockPcsCluster.Resource.State.STARTED
            )
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                dest_resource, MockPcsCluster.Resource.State.STARTED
            )
        )

        MockPcsCluster.constraints.append(
            MockPcsCluster.OrderingConstraint(
                source_resource,
                dest_resource,
                MockPcsCluster.OrderingConstraint.OrderType.START,
                MockPcsCluster.OrderingConstraint.OrderType.STOP,
                False,
            ),
        )

        set_module_args(
            {
                "constraint_type": "order",
                "state": "absent",
                "source_resource": source_resource,
                "dest_resource": dest_resource,
                "source_resource_order_type": "start",
                "dest_resource_order_type": "stop",
                "order_symmetric": False,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            constraint.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.constraints) == 0)

    def test_fail_if_dest_resource_order_type_is_not_valid(self) -> None:
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "constraint_type": "order",
                "state": "present",
                "source_resource": "something",
                "dest_resource": "awesome_resource",
                "source_resource_order_type": "start",
                "dest_resource_order_type": "invalid",
                "resource_order_action": "mandatory",
                "order_symmetric": False,
            },
        )
        with self.assertRaises(AnsibleFailJson):
            constraint.main()

    def test_fail_if_source_order_type_is_not_valid(self) -> None:
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "constraint_type": "order",
                "state": "present",
                "source_resource": "something",
                "dest_resource": "awesome_resource",
                "source_resource_order_type": "ciao",
                "dest_resource_order_type": "stop",
                "resource_order_action": "mandatory",
                "order_symmetric": False,
            },
        )
        with self.assertRaises(AnsibleFailJson):
            constraint.main()

    def test_fail_if_resource_present_different_resource_order_action(self) -> None:
        MockPcsCluster.cluster["present"] = True
        source_resource = "my_resource"
        dest_resource = "awesome_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                source_resource, MockPcsCluster.Resource.State.STARTED
            )
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                dest_resource, MockPcsCluster.Resource.State.STARTED
            )
        )

        MockPcsCluster.constraints.append(
            MockPcsCluster.OrderingConstraint(
                source_resource,
                dest_resource,
                MockPcsCluster.OrderingConstraint.OrderType.START,
                MockPcsCluster.OrderingConstraint.OrderType.STOP,
                False,
                MockPcsCluster.OrderingConstraint.ResourceOrderAction.MANDATORY,
            ),
        )

        set_module_args(
            {
                "constraint_type": "order",
                "state": "present",
                "source_resource": source_resource,
                "dest_resource": dest_resource,
                "source_resource_order_type": "start",
                "dest_resource_order_type": "stop",
                "resource_order_action": "optional",
                "order_symmetric": False,
            },
        )

        with self.assertRaises(AnsibleFailJson):
            constraint.main()

    def test_fail_if_resource_present_different_order_symmetric(self) -> None:
        MockPcsCluster.cluster["present"] = True
        source_resource = "my_resource"
        dest_resource = "awesome_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                source_resource, MockPcsCluster.Resource.State.STARTED
            )
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                dest_resource, MockPcsCluster.Resource.State.STARTED
            )
        )

        MockPcsCluster.constraints.append(
            MockPcsCluster.OrderingConstraint(
                source_resource,
                dest_resource,
                MockPcsCluster.OrderingConstraint.OrderType.START,
                MockPcsCluster.OrderingConstraint.OrderType.STOP,
                False,
                MockPcsCluster.OrderingConstraint.ResourceOrderAction.MANDATORY,
            ),
        )

        set_module_args(
            {
                "constraint_type": "order",
                "state": "present",
                "source_resource": source_resource,
                "dest_resource": dest_resource,
                "source_resource_order_type": "start",
                "dest_resource_order_type": "stop",
                "resource_order_action": "mandatory",
                "order_symmetric": True,
            },
        )

        with self.assertRaises(AnsibleFailJson):
            constraint.main()

    def test_no_change_when_order_constrain_exists(self) -> None:
        MockPcsCluster.cluster["present"] = True
        source_resource = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        dest_resource = "awesome_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                source_resource, MockPcsCluster.Resource.State.STARTED
            )
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                dest_resource, MockPcsCluster.Resource.State.STARTED
            )
        )

        MockPcsCluster.constraints.append(
            MockPcsCluster.OrderingConstraint(
                source_resource,
                dest_resource,
                MockPcsCluster.OrderingConstraint.OrderType.STOP,
                MockPcsCluster.OrderingConstraint.OrderType.START,
                True,
                MockPcsCluster.OrderingConstraint.ResourceOrderAction.OPTIONAL,
            ),
        )

        set_module_args(
            {
                "constraint_type": "order",
                "state": "present",
                "source_resource": source_resource,
                "dest_resource": dest_resource,
                "source_resource_order_type": "stop",
                "dest_resource_order_type": "start",
                "resource_order_action": "optional",
                "order_symmetric": True,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            constraint.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.constraints) == 1)

    def test_no_change_when_order_constrain_not_exists(self) -> None:
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "constraint_type": "order",
                "state": "absent",
                "source_resource": "something",
                "dest_resource": "testtesttest",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            constraint.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.constraints) == 0)

    def test_fail_when_cluster_doesnt_exist(self) -> None:
        MockPcsCluster.cluster["present"] = False

        set_module_args(
            {
                "constraint_type": "colocation",
                "state": "present",
                "source_resource": "something",
                "dest_resource": "testtesttest",
            },
        )
        with self.assertRaises(AnsibleFailJson):
            constraint.main()
