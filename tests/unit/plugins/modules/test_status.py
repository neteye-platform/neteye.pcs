import unittest
import os
import json

from plugins.modules import status
from tests.test_utils.mock_ansible import (
    set_module_args,
    AnsibleExitJson,
    patchAnsibleModule,
)
from tests.test_utils.mock_cluster_utils import patchClusterUtils


class TestStatus(unittest.TestCase):
    def setUp(self):
        self.patches = [
            patchAnsibleModule(),
            patchClusterUtils(),
        ]

        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_parse_pcs_status_xml_output(self):
        fixtures_dir = os.path.join(
            os.path.dirname(__file__), "../../../test_utils/fixtures/pcs_status/"
        )
        # Run the test with all the files xml files in the fixtures directory
        for file_name in [f for f in os.listdir(fixtures_dir) if f.endswith(".xml")]:
            with self.subTest(file_name=file_name):
                # Read the raw xml that will be used as input for the ansible module
                pcs_status_raw_xml = open(os.path.join(fixtures_dir, file_name)).read()

                # Read the expected dictionary that should be extracted from the raw xml above
                with open(
                    os.path.join(
                        fixtures_dir, file_name.replace(".xml", "_parsed.json")
                    )
                ) as f:
                    expected_pcs_module_parsed_output = json.load(f)

                # Parse the xml using the neteyepcs status module and check if the actual output matches the expected one
                parsed_output = status.parsePcsStatusXmlOutput(None, pcs_status_raw_xml)
                self.assertDictEqual(parsed_output, expected_pcs_module_parsed_output)

    def test_module_status(self):
        set_module_args({})
        with self.assertRaises(AnsibleExitJson) as _:
            status.main()
