from ansible_collections.neteye.pcs.plugins.module_utils import cluster as cluster_utils
from ansible_collections.neteye.pcs.tests.test_utils.mock_pcs_cluster import (
    MockPcsCluster,
)
from unittest.mock import patch, _patch


def checkIfPathExists(path: str) -> bool:
    if path:
        return MockPcsCluster.cluster["present"]
    return False


def patchClusterUtils() -> _patch:
    return patch.multiple(
        cluster_utils,
        checkIfPathExists=checkIfPathExists,
    )
