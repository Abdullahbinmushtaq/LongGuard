"""Documented lazy exports resolve without importing provider SDKs."""

import importlib

import pytest

import longguard


@pytest.mark.parametrize(
    "name,module",
    [
        ("LongGuard", "langgraph"),
        ("add_guard_to_graph", "langgraph"),
        ("compile_guarded_graph", "langgraph"),
        ("GuardedGraph", "graph_runner"),
        ("GuardedAgentExecutor", "langchain"),
        ("GuardTerminatedException", "langchain"),
        ("StrandsGuard", "strands"),
        ("GuardTerminatedError", "strands"),
        ("CrewGuard", "crewai"),
        ("add_guard_to_crew", "crewai"),
    ],
)
def test_documented_lazy_export_resolves_to_integration(name, module):
    adapter = importlib.import_module(f"longguard.integrations.{module}")
    assert getattr(longguard, name) is getattr(adapter, name)


def test_unknown_export_raises_standard_attribute_error():
    with pytest.raises(AttributeError, match="no attribute 'missing_export'"):
        getattr(longguard, "missing_export")
