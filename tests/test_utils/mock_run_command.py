from ansible_collections.neteye.pcs.tests.test_utils.mock_pcs_cluster import (
    FAILED_RC,
    RETURN_TYPE,
    SUCCEED_RC,
    MockPcsCluster,
)


def run_command(_, args: list) -> RETURN_TYPE:
    cmd = " ".join(args)
    # pcs command
    if cmd.startswith("pcs"):
        return MockPcsCluster.pcs(args, cmd)
    if cmd.startswith("crm"):
        return MockPcsCluster.crm(args, cmd)
    # check if qdevice is enabled
    if cmd.startswith("systemctl is-enabled --quiet corosync-qnetd.service"):
        if MockPcsCluster.qdevice["started"] and MockPcsCluster.qdevice["enabled"]:
            return SUCCEED_RC
        return FAILED_RC
    return None
