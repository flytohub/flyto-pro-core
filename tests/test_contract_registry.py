"""Integration contract between Flyto2 Core and the local contract registry."""

from __future__ import annotations

import pytest

from flyto_pro_core.contract.registry.contract_registry import ContractRegistry


@pytest.mark.asyncio
async def test_registry_loads_current_flyto_core_catalog() -> None:
    """Verify registry loads current flyto core catalog."""
    registry = ContractRegistry()

    await registry.initialize(load_from_core=True)

    assert len(registry.get_all()) >= 425
    assert registry.get("http.get") is not None
    assert registry.get("array.map") is not None
    assert registry.get("test.assert_equal") is not None
    assert registry.get("productivity.airtable.create") is not None
