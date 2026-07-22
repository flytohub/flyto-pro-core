"""Flyto2 Core parameter-schema compatibility tests."""

from __future__ import annotations

from flyto_pro_core.contract.models.params_schema import ParamType, ParamsSchema


def test_core_aliases_and_union_types_are_normalized() -> None:
    """Verify core aliases and union types are normalized."""
    schema = ParamsSchema.from_flyto_core_schema(
        {
            "text": {"type": "text", "required": True},
            "payload": {"type": "json"},
            "value": {"type": "any"},
            "actual": {"type": ["string", "number", "boolean"]},
        }
    )

    assert schema.params["text"].type is ParamType.STRING
    assert schema.params["payload"].type is ParamType.OBJECT
    assert schema.params["value"].type is ParamType.ANY
    assert schema.params["actual"].allowed_types == [
        ParamType.STRING,
        ParamType.NUMBER,
        ParamType.BOOLEAN,
    ]
    assert schema.params["actual"].validate(42)[0] is True
    assert schema.params["actual"].validate({"unexpected": True})[0] is False


def test_nested_validation_and_sensitive_flag_are_preserved() -> None:
    """Verify nested validation and sensitive flag are preserved."""
    schema = ParamsSchema.from_flyto_core_schema(
        {
            "token": {"type": "string", "sensitive": True},
            "timeout": {
                "type": "number",
                "validation": {"min": 1, "max": 30},
                "group": "advanced",
            },
        }
    )

    assert schema.params["token"].secret is True
    assert schema.params["timeout"].validation == {"min": 1, "max": 30}
    assert schema.params["timeout"].group == "advanced"
    assert schema.params["timeout"].validate(31) == (False, "Value must be <= 30")


def test_union_types_round_trip() -> None:
    """Verify union types round trip."""
    original = ParamsSchema.from_flyto_core_schema(
        {"value": {"type": ["string", "number"], "required": True}}
    )

    restored = ParamsSchema.from_dict(original.to_dict())

    assert restored.to_dict() == original.to_dict()
