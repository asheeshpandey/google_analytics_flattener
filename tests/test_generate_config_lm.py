from tests.test_base import BaseUnitTest
from tests.test_base import Context
from dmt_log_metric import GenerateConfig


class TestGenerateConfigLm(BaseUnitTest):
    
    def test_generate_config(self):
        c = Context()
        config = GenerateConfig(c)
        self.assertIsInstance(config, dict)
