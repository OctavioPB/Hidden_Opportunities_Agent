"""
Data sources layer.

In DEMO_MODE each module reads from the local SQLite database (seeded with
synthetic data). In production each module would call the real external API.

All modules expose the same interface so the agent never needs to know
which mode it is running in.
"""
