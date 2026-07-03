"""World core: authoritative tick-stepped state, intent validation, perception.

The world mutates only through intents validated against the action grammar
(schemas/json/agent_intent.schema.json). Cognition is async and the world
never blocks on a model.
"""
