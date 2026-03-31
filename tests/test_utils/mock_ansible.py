import json
from unittest.mock import _patch, patch

from ansible.module_utils import basic
from ansible.module_utils.common.text.converters import to_bytes
from ansible_collections.neteye.pcs.tests.test_utils.mock_run_command import run_command


def set_module_args(args):
    args = json.dumps({"ANSIBLE_MODULE_ARGS": args})
    basic._ANSIBLE_ARGS = to_bytes(args)


class AnsibleExitJson(Exception):
    pass


class AnsibleFailJson(Exception):
    pass


def exit_json(*_, **kwargs):
    if "changed" not in kwargs:
        kwargs["changed"] = False
    raise AnsibleExitJson(kwargs)


def fail_json(*_, **kwargs):
    kwargs["failed"] = True
    raise AnsibleFailJson(kwargs)


def patchAnsibleModule() -> _patch:
    return patch.multiple(
        basic.AnsibleModule,
        exit_json=exit_json,
        fail_json=fail_json,
        run_command=run_command,
    )
