"""
Contract Engine - Single Source of Truth for Module and Workflow Contracts

This is the brain's understanding of what modules can do, how they connect,
and how data flows between them. Cloud renders, Pro plans, Core validates.

Architecture:
    Core (flyto-core) = "hands" - atomic modules
    Pro (flyto-pro)   = "brain" - AI, evolution, THIS Contract Engine
    Cloud             = "face"  - UI rendering only

Key Principle: Cloud NEVER makes decisions. It asks Core (via this engine).

Key Components:
- ModuleContract: Defines ports, params, data types, connection policies
- WorkflowValidator: Validates workflow specs against contracts
- BindingResolver: Resolves variable bindings and scope
- WorkflowCompiler: Compiles specs into executable plans

Four Key APIs:
1. validate_workflow(spec) -> ValidationReport
2. get_connectability(module_id, port_id, direction) -> candidates
3. get_available_bindings(spec, node_id) -> BindingTree
4. compile(spec) -> ExecutablePlan

Usage:
    from flyto_pro_core.contract import ContractEngine, get_engine

    # Get initialized engine
    engine = await get_engine()

    # Validate a workflow
    report = await engine.validate_workflow(spec)

    # Get connectability for a port
    candidates = await engine.get_connectability("browser.goto", "out", "output")

    # Get available bindings for a node
    bindings = await engine.get_available_bindings(spec, "node_3")

    # Compile to executable plan
    plan = await engine.compile(spec)
"""

from .engine import ContractEngine, get_engine
from .models.port import Port, PortDirection, EdgeType, PortTemplates
from .models.data_contract import DataContract, DataType, ContractTemplates
from .models.params_schema import ParamsSchema, ParamDef, ParamType, ParamOption
from .models.module_contract import ModuleContract, ConnectionPolicy, ControlFlowContracts
from .models.workflow_spec import WorkflowSpec, NodeSpec, EdgeSpec
from .models.execution_result import ExecutionResult, ExecutionEvent, ScopeData, ExecutionTrace
from .registry.contract_registry import ContractRegistry, CatalogOutline, CatalogDetail
from .validator.workflow_validator import WorkflowValidator, ValidationReport, ValidationIssue
from .binder.binding_resolver import BindingResolver, BindingTree, BindingEntry, BindingSource
from .compiler.workflow_compiler import WorkflowCompiler, ExecutablePlan, CompiledNode, CompilationError

__all__ = [
    # Engine
    "ContractEngine",
    "get_engine",
    # Port models
    "Port",
    "PortDirection",
    "EdgeType",
    "PortTemplates",
    # Data models
    "DataContract",
    "DataType",
    "ContractTemplates",
    # Params
    "ParamsSchema",
    "ParamDef",
    "ParamType",
    "ParamOption",
    # Module contract
    "ModuleContract",
    "ConnectionPolicy",
    "ControlFlowContracts",
    # Workflow spec
    "WorkflowSpec",
    "NodeSpec",
    "EdgeSpec",
    # Execution result
    "ExecutionResult",
    "ExecutionEvent",
    "ScopeData",
    "ExecutionTrace",
    # Registry
    "ContractRegistry",
    "CatalogOutline",
    "CatalogDetail",
    # Validator
    "WorkflowValidator",
    "ValidationReport",
    "ValidationIssue",
    # Binder
    "BindingResolver",
    "BindingTree",
    "BindingEntry",
    "BindingSource",
    # Compiler
    "WorkflowCompiler",
    "ExecutablePlan",
    "CompiledNode",
    "CompilationError",
]
