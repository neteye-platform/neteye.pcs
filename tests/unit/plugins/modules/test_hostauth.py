import unittest

from ansible_collections.neteye.pcs.plugins.modules import hostauth
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
from typing import Union
from unittest.mock import patch


def getPassword(path: str) -> Union[None, str]:
    if path:
        return MockPcsCluster.cluster["password"]
    return None


class TestHostAuth(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patchAnsibleModule(),
            patchClusterUtils(),
            patch.multiple(
                hostauth,
                getPassword=getPassword,
            ),
        ]

        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_fail_when_required_args_missing(self):
        set_module_args({})
        with self.assertRaises(AnsibleFailJson):
            hostauth.main()

    def test_fail_when_cluster_exist(self):
        MockPcsCluster.cluster["present"] = True

        set_module_args(
            {
                "host": "neteye-cluster.neteyetest",
                "password_file": "/path/to/someware",
            }
        )
        with self.assertRaises(AnsibleFailJson):
            hostauth.main()

    def test_fail_when_password_empty(self):
        MockPcsCluster.cluster["present"] = False
        MockPcsCluster.cluster["password"] = None

        set_module_args(
            {
                "host": "neteye-cluster.neteyetest",
                "password_file": "/path/to/somewhere",
            }
        )
        with self.assertRaises(AnsibleFailJson):
            hostauth.main()

    def test_succeed_when_authing_a_node(self):
        MockPcsCluster.cluster["present"] = False
        MockPcsCluster.cluster["password"] = "password123"
        MockPcsCluster.cluster["authedNodes"] = []
        host = "neteye-cluster.neteyetest"

        set_module_args(
            {
                "host": host,
                "password_file": "/path/to/somewhere",
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            hostauth.main()

        self.assertTrue(result.exception.args[0]["changed"])
        self.assertTrue(host in MockPcsCluster.cluster["authedNodes"])

    def test_not_changed_when_node_is_already_auth(self):
        MockPcsCluster.cluster["present"] = False
        MockPcsCluster.cluster["password"] = "password123"
        host = "neteye-cluster.neteyetest"
        MockPcsCluster.cluster["authedNodes"] = [host]

        set_module_args(
            {
                "host": host,
                "password_file": "/path/to/somewhere",
            }
        )
        with self.assertRaises(AnsibleExitJson) as result:
            hostauth.main()

        self.assertFalse(result.exception.args[0]["changed"])
        self.assertTrue(host in MockPcsCluster.cluster["authedNodes"])
        self.assertTrue(len(MockPcsCluster.cluster["authedNodes"]) == 1)
