from ansible.module_utils.basic import AnsibleModule
from os.path import isfile

CLUSTER_FILE_PATH = "/etc/corosync/corosync.conf"


def checkIfPathExists(path: str) -> bool:
    return isfile(path)


def isAlreadyCluster(module: AnsibleModule) -> bool:
    cmd = ["pcs", "cluster", "config"]
    rc, _, _ = module.run_command(args=cmd)
    return checkIfPathExists(CLUSTER_FILE_PATH) and rc == 0
