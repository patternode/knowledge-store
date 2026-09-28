"""The knowledge graph as tools for other agents, served through AgentCore Gateway (MCP).

The tools are the same functions the portal's chat uses (portal_api.chat.run_tool), plus the
ones a task agent needs and a chat does not: list the collections, and fetch a released
ontology rendition. One implementation, two surfaces, so they cannot drift apart.
"""
