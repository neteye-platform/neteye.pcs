import unittest

from ansible_collections.neteye.pcs.plugins.modules import qdevice
from ansible_collections.neteye.pcs.tests.test_utils.mock_ansible import (
    AnsibleExitJson,
    AnsibleFailJson,
    patchAnsibleModule,
    set_module_args,
)
from ansible_collections.neteye.pcs.tests.test_utils.mock_pcs_cluster import (
    MockPcsCluster,
)
from unittest.mock import patch


def isQdevicePresent(_: str) -> bool:
    return MockPcsCluster.qdevice["present"]


class TestQdevice(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patchAnsibleModule(),
            patch.multiple(
                qdevice,
                isQdevicePresent=isQdevicePresent,
            ),
        ]

        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_fail_when_required_args_missing(self):
        set_module_args({})
        with self.assertRaises(AnsibleFailJson):
            qdevice.main()

    def test_succeed_when_creating_new_qdevice(self):
        MockPcsCluster.qdevice["enabled"] = False
        MockPcsCluster.qdevice["present"] = False
        MockPcsCluster.qdevice["started"] = False

        set_module_args(
            {
                "state": "started",
                "enabled": True,
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            qdevice.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.qdevice["enabled"])
        self.assertTrue(MockPcsCluster.qdevice["present"])
        self.assertTrue(MockPcsCluster.qdevice["started"])

    def test_succeed_when_destroy_new_qdevice(self):
        MockPcsCluster.qdevice["present"] = True

        set_module_args(
            {
                "state": "absent",
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            qdevice.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertFalse(MockPcsCluster.qdevice["present"])

    def test_no_change_when_qdevice_not_present(self):
        MockPcsCluster.qdevice["present"] = False
        MockPcsCluster.qdevice["started"] = False
        MockPcsCluster.qdevice["enabled"] = False

        set_module_args(
            {
                "state": "absent",
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            qdevice.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertFalse(MockPcsCluster.qdevice["present"])
        self.assertFalse(MockPcsCluster.qdevice["started"])
        self.assertFalse(MockPcsCluster.qdevice["enabled"])

    def test_no_change_when_qdevice_present(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["started"] = False
        MockPcsCluster.qdevice["enabled"] = False

        set_module_args(
            {
                "state": "present",
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            qdevice.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.qdevice["present"])
        self.assertFalse(MockPcsCluster.qdevice["started"])
        self.assertFalse(MockPcsCluster.qdevice["enabled"])

    def test_no_change_when_qdevice_started(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["started"] = True
        MockPcsCluster.qdevice["enabled"] = False

        set_module_args(
            {
                "state": "started",
                "enabled": False,
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            qdevice.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.qdevice["present"])
        self.assertTrue(MockPcsCluster.qdevice["started"])
        self.assertFalse(MockPcsCluster.qdevice["enabled"])

    def test_succeed_start_when_qdevice_stopped(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["started"] = False
        MockPcsCluster.qdevice["enabled"] = False

        set_module_args(
            {
                "state": "started",
                "enabled": False,
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            qdevice.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.qdevice["present"])
        self.assertTrue(MockPcsCluster.qdevice["started"])
        self.assertFalse(MockPcsCluster.qdevice["enabled"])

    def test_succeed_stop_when_qdevice_started(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["started"] = True
        MockPcsCluster.qdevice["enabled"] = False

        set_module_args(
            {
                "state": "stopped",
                "enabled": False,
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            qdevice.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.qdevice["present"])
        self.assertFalse(MockPcsCluster.qdevice["started"])
        self.assertFalse(MockPcsCluster.qdevice["enabled"])

    def test_succeed_disable_when_qdevice_enabled(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["started"] = True
        MockPcsCluster.qdevice["enabled"] = True

        set_module_args(
            {
                "state": "started",
                "enabled": False,
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            qdevice.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.qdevice["present"])
        self.assertTrue(MockPcsCluster.qdevice["started"])
        self.assertFalse(MockPcsCluster.qdevice["enabled"])

    def test_succeed_enable_when_qdevice_disabled(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["started"] = True
        MockPcsCluster.qdevice["enabled"] = False

        set_module_args(
            {
                "state": "started",
                "enabled": True,
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            qdevice.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.qdevice["present"])
        self.assertTrue(MockPcsCluster.qdevice["started"])
        self.assertTrue(MockPcsCluster.qdevice["enabled"])
