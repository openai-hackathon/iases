import asyncio
import unittest
from types import SimpleNamespace

from experiments.semantic_router_probe import collect


class SemanticRouterProbeTest(unittest.IsolatedAsyncioTestCase):
    async def test_requires_successful_tool_output_and_final_confirmation(self):
        for status, exit_code, output, final, expected in [
            (
                "completed",
                0,
                "semantic-router-tool-ok\n",
                "semantic-router-confirmed",
                True,
            ),
            (
                "failed",
                1,
                "semantic-router-tool-ok\n",
                "semantic-router-confirmed",
                False,
            ),
            ("completed", 0, "unrelated", "semantic-router-confirmed", False),
            ("completed", 0, "semantic-router-tool-ok\n", "", False),
        ]:
            with self.subTest(status=status, output=output, final=final):
                client = SimpleNamespace(events=asyncio.Queue())
                for item in [
                    {
                        "type": "commandExecution",
                        "status": status,
                        "exitCode": exit_code,
                        "aggregatedOutput": output,
                    },
                    {"type": "agentMessage", "text": final},
                ]:
                    client.events.put_nowait(
                        {"method": "item/completed", "params": {"item": item}}
                    )
                client.events.put_nowait(
                    {
                        "method": "turn/completed",
                        "params": {"turn": {"status": "completed"}},
                    }
                )
                report = await collect(client)
                self.assertEqual(report["passed"], expected)

    async def test_does_not_accept_text_without_a_tool(self):
        client = SimpleNamespace(events=asyncio.Queue())
        client.events.put_nowait(
            {
                "method": "item/completed",
                "params": {
                    "item": {
                        "type": "agentMessage",
                        "text": "semantic-router-confirmed",
                    },
                },
            }
        )
        client.events.put_nowait(
            {"method": "turn/completed", "params": {"turn": {"status": "completed"}}}
        )
        self.assertEqual(
            await collect(client),
            {
                "status": "completed",
                "tool_completed": False,
                "final_text": "semantic-router-confirmed",
                "passed": False,
            },
        )
