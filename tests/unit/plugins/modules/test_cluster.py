import unittest

from ansible_collections.neteye.pcs.plugins.modules import cluster
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


def compareClusterNames(cluster_name: str) -> bool:
    return MockPcsCluster.cluster["name"] == cluster_name


def compareClusterNodes(nodes: list) -> bool:
    return all(host in MockPcsCluster.cluster["authedNodes"] for host in nodes)


class TestCluster(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patchAnsibleModule(),
            patchClusterUtils(),
            patch.multiple(
                cluster,
                compareClusterNames=compareClusterNames,
                compareClusterNodes=compareClusterNodes,
            ),
        ]

        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_fail_when_required_args_missing(self):
        set_module_args({})
        with self.assertRaises(AnsibleFailJson):
            cluster.main()

    def test_fail_when_only_one_node_is_provided(self):
        set_module_args(
            {
                "state": "present",
                "nodes": ["neteye-cluster1.neteyetest"],
            }
        )
        with self.assertRaises(AnsibleFailJson):
            cluster.main()

    def test_fail_when_not_all_nodes_are_authed(self):
        MockPcsCluster.cluster["present"] = False
        MockPcsCluster.cluster["authedNodes"] = [
            "neteye-cluster1.neteyetest",
            "neteye-cluster2.neteyetest",
        ]

        set_module_args(
            {
                "state": "present",
                "nodes": [
                    "neteye-cluster1.neteyetest",
                    "neteye-cluster2.neteyetest",
                    "neteye-cluster3.neteyetest",
                ],
            }
        )
        with self.assertRaises(AnsibleFailJson):
            cluster.main()

    def test_fail_when_cluster_is_already_started(self):
        MockPcsCluster.cluster["present"] = True
        MockPcsCluster.cluster["authedNodes"] = [
            "neteye-cluster1.neteyetest",
            "neteye-cluster2.neteyetest",
        ]

        set_module_args(
            {
                "state": "present",
                "nodes": MockPcsCluster.cluster["authedNodes"],
            }
        )
        with self.assertRaises(AnsibleExitJson):
            cluster.main()

    def test_succeed_and_started_when_creating_new_cluster(self):
        MockPcsCluster.cluster["present"] = False
        MockPcsCluster.cluster["started"] = False
        MockPcsCluster.cluster["enabled"] = False
        MockPcsCluster.cluster["authedNodes"] = [
            "neteye-cluster1.neteyetest",
            "neteye-cluster2.neteyetest",
        ]

        set_module_args(
            {
                "state": "started",
                "nodes": MockPcsCluster.cluster["authedNodes"],
                "enabled": True,
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            cluster.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.cluster["present"])
        self.assertTrue(MockPcsCluster.cluster["started"])
        self.assertTrue(MockPcsCluster.cluster["enabled"])

    def test_succeed_and_not_started_when_creating_new_cluster(self):
        MockPcsCluster.cluster["present"] = False
        MockPcsCluster.cluster["started"] = False
        MockPcsCluster.cluster["enabled"] = False
        MockPcsCluster.cluster["authedNodes"] = [
            "neteye-cluster1.neteyetest",
            "neteye-cluster2.neteyetest",
        ]

        set_module_args(
            {
                "state": "present",
                "nodes": MockPcsCluster.cluster["authedNodes"],
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            cluster.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.cluster["present"])
        self.assertFalse(MockPcsCluster.cluster["started"])
        self.assertFalse(MockPcsCluster.cluster["enabled"])

    def test_succeed_if_cluster_exists_and_forced(self):
        MockPcsCluster.cluster["present"] = True
        MockPcsCluster.cluster["started"] = False
        MockPcsCluster.cluster["enabled"] = False
        MockPcsCluster.cluster["recreated"] = False
        MockPcsCluster.cluster["name"] = "NetEye"
        MockPcsCluster.cluster["authedNodes"] = [
            "neteye-cluster1.neteyetest",
            "neteye-cluster2.neteyetest",
        ]

        set_module_args(
            {
                "state": "started",
                "nodes": MockPcsCluster.cluster["authedNodes"],
                "force": True,
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            cluster.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.cluster["present"])
        self.assertTrue(MockPcsCluster.cluster["started"])
        self.assertTrue(MockPcsCluster.cluster["enabled"])
        self.assertTrue(MockPcsCluster.cluster["recreated"])

    def test_fail_if_cluster_name_is_different(self):
        MockPcsCluster.cluster["present"] = True
        MockPcsCluster.cluster["started"] = True
        MockPcsCluster.cluster["enabled"] = False
        MockPcsCluster.cluster["name"] = "FakeNetEye"
        MockPcsCluster.cluster["authedNodes"] = [
            "neteye-cluster1.neteyetest",
            "neteye-cluster2.neteyetest",
        ]

        set_module_args(
            {
                "state": "started",
                "nodes": MockPcsCluster.cluster["authedNodes"],
            }
        )
        with self.assertRaises(AnsibleFailJson):
            cluster.main()

    def test_fail_if_cluster_exists_and_absent(self):
        MockPcsCluster.cluster["present"] = True

        set_module_args({"state": "absent"})
        with self.assertRaises(AnsibleFailJson):
            cluster.main()

    def test_no_change_if_cluster_not_exists_and_absent(self):
        MockPcsCluster.cluster["present"] = False

        set_module_args({"state": "absent"})
        with self.assertRaises(AnsibleExitJson) as result:
            cluster.main()

        self.assertFalse(result.exception.args[0]["changed"])

    def test_no_change_if_cluster_exists_and_not_force(self):
        MockPcsCluster.cluster["present"] = True
        MockPcsCluster.cluster["started"] = True
        MockPcsCluster.cluster["enabled"] = True
        MockPcsCluster.cluster["recreated"] = False
        MockPcsCluster.cluster["name"] = "NetEye"
        MockPcsCluster.cluster["authedNodes"] = [
            "neteye-cluster1.neteyetest",
            "neteye-cluster2.neteyetest",
        ]

        set_module_args(
            {
                "state": "started",
                "nodes": MockPcsCluster.cluster["authedNodes"],
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            cluster.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.cluster["present"])
        self.assertTrue(MockPcsCluster.cluster["started"])
        self.assertTrue(MockPcsCluster.cluster["enabled"])
        self.assertFalse(MockPcsCluster.cluster["recreated"])

    def test_no_change_if_cluster_started_case_1(self):
        MockPcsCluster.cluster["present"] = True
        MockPcsCluster.cluster["started"] = True
        MockPcsCluster.cluster["enabled"] = True
        MockPcsCluster.cluster["recreated"] = False
        MockPcsCluster.cluster["name"] = "NetEye"

        set_module_args(
            {
                "state": "started",
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            cluster.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.cluster["present"])
        self.assertTrue(MockPcsCluster.cluster["started"])
        self.assertTrue(MockPcsCluster.cluster["enabled"])
        self.assertFalse(MockPcsCluster.cluster["recreated"])

    def test_no_change_if_cluster_started_case_2(self):
        MockPcsCluster.cluster["present"] = True
        MockPcsCluster.cluster["started"] = True
        MockPcsCluster.cluster["enabled"] = True
        MockPcsCluster.cluster["recreated"] = False
        MockPcsCluster.cluster["name"] = "NetEye"
        MockPcsCluster.cluster["authedNodes"] = [
            "neteye-cluster1.neteyetest",
            "neteye-cluster2.neteyetest",
        ]

        set_module_args(
            {
                "state": "started",
                "nodes": MockPcsCluster.cluster["authedNodes"],
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            cluster.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertTrue(MockPcsCluster.cluster["present"])
        self.assertTrue(MockPcsCluster.cluster["started"])
        self.assertTrue(MockPcsCluster.cluster["enabled"])
        self.assertFalse(MockPcsCluster.cluster["recreated"])
