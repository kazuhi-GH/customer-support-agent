import os
import unittest

os.environ.setdefault("PROJECT_ENDPOINT", "https://example.services.ai.azure.com/api/projects/test")

from azure.ai.projects.models import MCPTool, WebSearchTool

from agent import SYSTEM_INSTRUCTIONS
from tools import TOOL_DEFINITIONS


class WebSearchToolTests(unittest.TestCase):
    def test_live_web_search_is_registered(self):
        web_search_tools = [tool for tool in TOOL_DEFINITIONS if isinstance(tool, WebSearchTool)]

        self.assertEqual(len(web_search_tools), 1)
        self.assertTrue(web_search_tools[0].external_web_access)
        self.assertEqual(web_search_tools[0].search_context_size, "high")

    def test_agent_prioritizes_official_sources_and_cites_them(self):
        self.assertIn("web_search", SYSTEM_INSTRUCTIONS)
        self.assertIn("Microsoft Learn", SYSTEM_INSTRUCTIONS)
        self.assertIn("リンク", SYSTEM_INSTRUCTIONS)

    def test_microsoft_learn_mcp_is_registered(self):
        mcp_tools = [tool for tool in TOOL_DEFINITIONS if isinstance(tool, MCPTool)]

        self.assertEqual(len(mcp_tools), 1)
        self.assertEqual(mcp_tools[0].server_label, "microsoft_learn")
        self.assertEqual(mcp_tools[0].server_url, "https://learn.microsoft.com/api/mcp")
        self.assertEqual(mcp_tools[0].require_approval, "never")
        self.assertIn("microsoft_learn", SYSTEM_INSTRUCTIONS)
        self.assertIn("Azure サポート", SYSTEM_INSTRUCTIONS)


if __name__ == "__main__":
    unittest.main()
