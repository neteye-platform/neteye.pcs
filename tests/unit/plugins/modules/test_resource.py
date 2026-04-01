import unittest

from ansible_collections.neteye.pcs.plugins.modules import resource
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

DEFAULT_TIMEOUT = 240


def check_if_path_exists(path: str) -> bool:
    if path:
        return MockPcsCluster.cluster["present"]
    return False


class TestResource(unittest.TestCase):
    def setUp(self) -> None:
        self.patches = [patchAnsibleModule(), patchClusterUtils()]

        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_fail_when_required_args_missing(self) -> None:
        set_module_args({})
        with self.assertRaises(AnsibleFailJson):
            resource.main()

    def test_succeed_when_create_new_resource_case_1(self) -> None:
        MockPcsCluster.cluster["present"] = True
        my_name = "my_resource"
        my_type = "my_type"
        my_options = ["my_option=my_value", "my_other_option=my_other_value"]
        my_op = [
            ["monitor", "interval=30s"],
            ["something", "somethingElse"],
        ]

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
                "resource_type": my_type,
                "resource_options": my_options,
                "operation_actions": my_op,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        my_op = [item for sublist in my_op for item in sublist]

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.name == my_name)
        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.res_type == my_type)
        self.assertTrue(set(res.op) == set(my_op))
        self.assertTrue(set(res.options) == set(my_options))
        self.assertTrue(res.group is None)
        self.assertTrue(res.state_applies == [("disable", DEFAULT_TIMEOUT)])

    def test_succeed_when_create_new_resource_case_2(self) -> None:
        MockPcsCluster.cluster["present"] = True
        my_name = "my_resource"
        my_type = "my_type"
        my_options = "my_option=my_value"
        my_op = [
            "monitor",
            "interval=30s",
            "something",
            "somethingElse",
        ]

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
                "resource_type": my_type,
                "resource_options": my_options,
                "operation_actions": my_op,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        my_options = [my_options]

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.name == my_name)
        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.res_type == my_type)
        self.assertTrue(set(res.op) == set(my_op))
        self.assertTrue(set(res.options) == set(my_options))
        self.assertTrue(res.group is None)
        self.assertTrue(res.state_applies == [("disable", DEFAULT_TIMEOUT)])

    def test_succeed_when_create_new_resource_case_3(self) -> None:
        MockPcsCluster.cluster["present"] = True
        my_name = "my_resource"
        my_type = "my_type"

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
                "resource_type": my_type,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.name == my_name)
        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.res_type == my_type)
        self.assertTrue(set(res.op) == set())
        self.assertTrue(set(res.options) == set())
        self.assertTrue(res.group is None)
        self.assertTrue(res.state_applies == [("disable", DEFAULT_TIMEOUT)])

    def test_succeed_when_create_new_resource_case_4(self) -> None:
        MockPcsCluster.cluster["present"] = True
        my_name = "my_resource"
        my_type = "my_type"
        my_options = "my_option=my_value"

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
                "resource_type": my_type,
                "resource_options": my_options,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        my_options = [my_options]

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.name == my_name)
        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.res_type == my_type)
        self.assertTrue(set(res.op) == set())
        self.assertTrue(set(res.options) == set(my_options))
        self.assertTrue(res.group is None)
        self.assertTrue(res.state_applies == [("disable", DEFAULT_TIMEOUT)])

    def test_succeed_when_create_new_resource_case_5(self) -> None:
        MockPcsCluster.cluster["present"] = True
        my_name = "my_resource"
        my_type = "my_type"
        my_op = [
            "monitor",
            "interval=30s",
            "something",
            "somethingElse",
        ]

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
                "resource_type": my_type,
                "operation_actions": my_op,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.name == my_name)
        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.res_type == my_type)
        self.assertTrue(set(res.op) == set(my_op))
        self.assertTrue(set(res.options) == set())
        self.assertTrue(res.group is None)
        self.assertTrue(res.state_applies == [("disable", DEFAULT_TIMEOUT)])

    def test_succeed_when_create_new_resource_case_6(self) -> None:
        MockPcsCluster.cluster["present"] = True
        my_group = "gruppie"
        my_name = "my_resource"
        my_type = "my_type"
        my_op = [
            "monitor",
            "interval=30s",
            "something",
            "somethingElse",
        ]

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
                "resource_type": my_type,
                "operation_actions": my_op,
                "group": my_group,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.name == my_name)
        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.res_type == my_type)
        self.assertTrue(set(res.op) == set(my_op))
        self.assertTrue(set(res.options) == set())
        self.assertTrue(res.group == my_group)
        self.assertTrue(res.state_applies == [("disable", DEFAULT_TIMEOUT)])

    def test_fail_when_no_type(self) -> None:
        MockPcsCluster.cluster["present"] = True
        my_name = "my_resource"

        set_module_args(
            {
                "name": my_name,
                "state": "present",
            },
        )
        with self.assertRaises(AnsibleFailJson):
            resource.main()

        self.assertTrue(len(MockPcsCluster.resources) == 0)

    def test_no_change_when_resource_exits_and_present_case_1(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.DISABLED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "present",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)
        self.assertTrue(res.state_applies == [])

    def test_no_change_when_resource_exits_and_present_case_2(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.STARTED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "present",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)
        self.assertTrue(res.state_applies == [])
        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)

    def test_no_change_when_resource_exits_and_present_case_3(self) -> None:
        my_name = "my_resource"
        my_group = "my_group"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.STARTED,
                group=my_group,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "present",
                "group": my_group,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)
        self.assertTrue(res.state_applies == [])
        self.assertTrue(res.group == my_group)
        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)

    def test_no_change_when_resource_exits_and_started(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.STARTED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "started",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)
        self.assertTrue(res.state_applies == [])
        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)

    def test_no_change_when_resource_exits_and_stopped(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.DISABLED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)
        self.assertTrue(res.state_applies == [])
        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)

    def test_no_change_when_resource_exits(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.cluster["present"] = True
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.DISABLED),
        )
        my_type = "my_type"
        my_options = "my_option=my_value"
        my_op = [
            "monitor",
            "interval=30s",
            "something",
            "somethingElse",
        ]

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
                "resource_type": my_type,
                "resource_options": my_options,
                "operation_actions": my_op,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)
        self.assertTrue(res.state_applies == [])
        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)

    def test_no_change_when_resource_not_exists(self) -> None:
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": "my_resource",
                "state": "absent",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 0)

    def test_succeed_when_start_resource_case_1(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.DISABLED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "started",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("enable", DEFAULT_TIMEOUT)])

    def test_succeed_when_start_resource_case_2(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.DISABLED),
        )
        MockPcsCluster.cluster["present"] = True
        timeout = 30

        set_module_args(
            {
                "name": my_name,
                "state": "started",
                "timeout": timeout,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("enable", timeout)])

    def test_succeed_when_stop_resource_case_1(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.STARTED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.state_applies == [("disable", DEFAULT_TIMEOUT)])

    def test_succeed_when_stop_resource_case_2(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.STARTED),
        )
        MockPcsCluster.cluster["present"] = True
        timeout = 30

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
                "timeout": timeout,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.state_applies == [("disable", timeout)])

    def test_succeed_when_restart_case_1(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.STARTED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "restarted",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("restart", DEFAULT_TIMEOUT)])

    def test_succeed_when_restart_case_2(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.STARTED),
        )
        MockPcsCluster.cluster["present"] = True
        timeout = 30

        set_module_args(
            {
                "name": my_name,
                "state": "restarted",
                "timeout": timeout,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)

        self.assertTrue(res.state_applies == [("restart", timeout)])

    def test_succeed_when_cleanedup_case_1(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.FAILED_ALL),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "cleanedup",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("cleanup", None)])

    def test_succeed_when_cleanedup_case_2(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.FAILED_PARTIAL,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "cleanedup",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("cleanup", None)])

    def test_succeed_when_cleanedup_case_3(self) -> None:
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": "*",
                "state": "cleanedup",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.cleanup_all_resources_count == 1)

    def test_no_change_when_cleanedup(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.STARTED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "cleanedup",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [])

    def test_fail_if_wildcard_and_not_cleanedup(self) -> None:
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": "*",
                "state": "started",
            },
        )
        with self.assertRaises(AnsibleFailJson):
            resource.main()

    def test_fail_when_group_is_different(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.STARTED,
                group="group_group",
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "present",
                "group": "anotherGroup",
            },
        )
        with self.assertRaises(AnsibleFailJson):
            resource.main()

    def test_fail_if_no_resource_and_cleanedup(self) -> None:
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": "FakeResource",
                "state": "cleanedup",
            },
        )
        with self.assertRaises(AnsibleFailJson):
            resource.main()

    def test_fail_if_no_resource_and_restarted(self) -> None:
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": "FakeResource",
                "state": "restarted",
            },
        )
        with self.assertRaises(AnsibleFailJson):
            resource.main()

    def test_succeed_when_destroy_resource(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.STARTED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "absent",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(len(MockPcsCluster.resources) == 0)

    def test_fail_if_no_cluster(self) -> None:
        MockPcsCluster.cluster["present"] = False

        set_module_args(
            {
                "name": "my_cluster",
                "state": "absent",
            },
        )
        with self.assertRaises(AnsibleFailJson):
            resource.main()

    def test_module_leave_started_resource_managed(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.STARTED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "present",
            },
        )

        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [])
        self.assertTrue(res.managed)

    def test_module_leave_stopped_resource_managed(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.DISABLED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "present",
            },
        )

        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.state_applies == [])
        self.assertTrue(res.managed)

    def test_module_manage_started_resource(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.STARTED,
                managed=False,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "managed",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("manage", None)])
        self.assertTrue(res.managed)

    def test_module_unmanage_started_resource(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.STARTED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "unmanaged",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("unmanage", None)])
        self.assertFalse(res.managed)

    def test_module_manage_stopped_resource(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.DISABLED,
                managed=False,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "managed",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.state_applies == [("manage", None)])
        self.assertTrue(res.managed)

    def test_module_unmanage_stopped_resource(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.DISABLED),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "unmanaged",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.state_applies == [("unmanage", None)])
        self.assertFalse(res.managed)

    def test_module_fail_if_resource_is_unamanged(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.DISABLED,
                managed=False,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "started",
            },
        )

        with self.assertRaises(AnsibleFailJson):
            resource.main()

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.state_applies == [])
        self.assertFalse(res.managed)

    def test_module_not_fail_if_unmanaged_and_desired_resource_1(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.STARTED,
                managed=False,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "started",
            },
        )

        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)
        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [])
        self.assertFalse(res.managed)

    def test_module_not_fail_if_unmanaged_and_desired_resource_2(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.DISABLED,
                managed=False,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "stopped",
            },
        )

        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)
        self.assertFalse(result.exception.args[0]["changed"])

        self.assertTrue(res.state == MockPcsCluster.Resource.State.DISABLED)
        self.assertTrue(res.state_applies == [])
        self.assertFalse(res.managed)

    def test_module_restart_failed_resource_on_all_nodes(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.FAILED_ALL),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "restarted",
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 1)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("cleanup", None)])

    def test_timeout_when_resource_in_action(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.STARTING,
                in_action=True,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "restarted",
                "timeout": 1,
                "check_interval": 1,
            },
        )
        with self.assertRaises(AnsibleFailJson):
            resource.main()

    def test_timeout_when_resource_in_transition(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.STARTING,
                in_transition=True,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "restarted",
                "timeout": 1,
                "check_interval": 1,
            },
        )
        with self.assertRaises(AnsibleFailJson):
            resource.main()

    def test_timeout_when_resource_in_action_and_transition(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.STARTING,
                in_transition=True,
                in_action=True,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "restarted",
                "timeout": 1,
                "check_interval": 1,
            },
        )
        with self.assertRaises(AnsibleFailJson):
            resource.main()

    def test_when_other_resource_in_action(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                my_name,
                MockPcsCluster.Resource.State.FAILED_ALL,
            ),
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                "other_my_resource",
                MockPcsCluster.Resource.State.STARTING,
                in_action=True,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "restarted",
                "timeout": 1,
                "check_interval": 1,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 2)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("cleanup", None)])

    def test_when_other_resource_in_transition(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.FAILED_ALL),
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                "other_my_resource",
                MockPcsCluster.Resource.State.STARTING,
                in_transition=True,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "restarted",
                "timeout": 1,
                "check_interval": 1,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 2)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("cleanup", None)])

    def test_when_other_resource_in_action_and_transition(self) -> None:
        my_name = "my_resource"
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(my_name, MockPcsCluster.Resource.State.FAILED_ALL),
        )
        MockPcsCluster.resources.append(
            MockPcsCluster.Resource(
                "other_my_resource",
                MockPcsCluster.Resource.State.STARTING,
                in_action=True,
                in_transition=True,
            ),
        )
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "name": my_name,
                "state": "restarted",
                "timeout": 1,
                "check_interval": 1,
            },
        )
        with self.assertRaises(AnsibleExitJson) as result:
            resource.main()

        self.assertTrue(result.exception.args[0]["changed"])

        self.assertTrue(len(MockPcsCluster.resources) == 2)
        res = next(r for r in MockPcsCluster.resources if r.name == my_name)

        self.assertTrue(res.state == MockPcsCluster.Resource.State.STARTED)
        self.assertTrue(res.state_applies == [("cleanup", None)])
