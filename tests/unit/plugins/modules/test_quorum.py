import unittest

from ansible_collections.neteye.pcs.plugins.modules import quorum
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
from unittest.mock import patch


def findQdeviceHostname() -> str:
    return MockPcsCluster.qdevice["host"]


def findQdeviceAlgorithm() -> str:
    return MockPcsCluster.qdevice["algorithm"]


class TestQuorum(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patchAnsibleModule(),
            patchClusterUtils(),
            patch.multiple(
                quorum,
                findQdeviceHostname=findQdeviceHostname,
                findQdeviceAlgorithm=findQdeviceAlgorithm,
            ),
        ]

        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_fail_when_required_args_missing(self):
        set_module_args({})
        with self.assertRaises(AnsibleFailJson):
            quorum.main()

    def test_no_changed_when_qdevice_present_case_1(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["host"] = "neteye-cluster.neteyetest"
        MockPcsCluster.qdevice["algorithm"] = "ffsplit"
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "state": "present",
                "host": MockPcsCluster.qdevice["host"],
                "algorithm": MockPcsCluster.qdevice["algorithm"],
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            quorum.main()

        self.assertFalse(result.exception.args[0]["changed"])

    def test_no_changed_when_qdevice_present_case_2(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["host"] = "neteye-cluster.neteyetest"
        MockPcsCluster.qdevice["algorithm"] = "ffsplit"
        MockPcsCluster.cluster["present"] = True

        set_module_args({"state": "present"})
        with self.assertRaises(AnsibleExitJson) as result:
            quorum.main()

        self.assertFalse(result.exception.args[0]["changed"])

    def test_fail_when_hostname_is_different(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["host"] = "neteye-cluster.neteyetest"
        MockPcsCluster.qdevice["algorithm"] = "ffsplit"
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "state": "present",
                "host": "something-else.neteyelocal",
                "algorithm": MockPcsCluster.qdevice["algorithm"],
            }
        )
        with self.assertRaises(AnsibleFailJson):
            quorum.main()

    def test_fail_when_algo_is_different(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["host"] = "neteye-cluster.neteyetest"
        MockPcsCluster.qdevice["algorithm"] = "ffsplit"
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "host": MockPcsCluster.qdevice["host"],
                "algorithm": "lms",
            }
        )
        with self.assertRaises(AnsibleFailJson):
            quorum.main()

    def test_succeed_when_destroy_qdevice(self):
        MockPcsCluster.qdevice["present"] = True
        MockPcsCluster.qdevice["host"] = "neteye-cluster.neteyetest"
        MockPcsCluster.qdevice["algorithm"] = "ffsplit"
        MockPcsCluster.cluster["present"] = True

        set_module_args({"state": "absent"})
        with self.assertRaises(AnsibleExitJson) as result:
            quorum.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertFalse(MockPcsCluster.qdevice["present"])

    def test_succeed_when_creating_qdevice(self):
        MockPcsCluster.qdevice["present"] = False
        MockPcsCluster.cluster["present"] = True
        host = "neteye-device.neteyetest"
        algorithm = "lms"

        set_module_args(
            {
                "state": "present",
                "host": host,
                "algorithm": algorithm,
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            quorum.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.qdevice["present"])
        self.assertTrue(MockPcsCluster.qdevice["host"] == host)
        self.assertTrue(MockPcsCluster.qdevice["algorithm"] == algorithm)
        self.assertTrue(MockPcsCluster.qdevice["model"] == "net")

    def test_fail_when_no_cluster(self):
        MockPcsCluster.cluster["present"] = False

        set_module_args(
            {
                "state": "present",
                "host": "my_host",
                "algorithm": "lms",
            }
        )
        with self.assertRaises(AnsibleFailJson):
            quorum.main()
