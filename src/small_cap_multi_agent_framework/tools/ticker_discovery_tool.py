# small_cap_multi_agent_framework/tools/ticker_discovery_tool.py
from crewai_tools import BaseTool

class TickerDiscoveryTool(BaseTool):
    name: str = "Ticker Discovery Tool"
    description: str = "Use this tool to get a list of promising small-cap stock tickers to analyze. No input is required."

    def _run(self) -> list[str]:
        """Returns a predefined list of small-cap tickers."""
        # For this example, we use a hard-coded list.
        # This can be expanded to fetch tickers from a stock screener API or a database.
        print("INFO: TickerDiscoveryTool is fetching the list of tickers...")
        return ["RKLB", "PL", "ASTS", "BKSY", "VLD", "IONQ"]

# Instantiate the tool for easy import
ticker_discovery_tool = TickerDiscoveryTool()