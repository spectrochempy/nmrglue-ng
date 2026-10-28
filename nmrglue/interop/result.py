"""Neutral, dependency-free result objects for the optional interop layer.

The objects here describe a reader output without knowing any vendor
dictionary.  They are additive: the historical ``(dic, data)`` reader APIs
are neither changed nor replaced.

Immutability is part of the contract:

* every dataclass is frozen (attribute rebinding raises);
* every exposed array is marked read-only (its ``writeable`` flag is cleared);
* mappings are exposed as read-only :class:`~types.MappingProxyType` views at
  the top level.  Deep immutability of nested values is not promised.

Diagnostic codes and their ``context`` schemas are declared normatively in
:data:`DIAGNOSTIC_CONTEXT_SCHEMA`, which fixes the keys and the container
types.  The elements of those containers are validated too: processing
parameter names, component names and sizes must be coherent.  Constructing a
:class:`Diagnostic` whose code is unknown, whose ``context`` is out of schema,
or whose severity is not ``info`` or ``warning`` raises ``ValueError``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, Mapping

import numpy as np

Domain = Literal["frequency", "time", "index", "unknown"]
Direction = Literal["increasing", "decreasing", "constant", "unknown"]
Severity = Literal["info", "warning"]
ReferenceSource = Literal["processing", "acquisition", "unknown"]

DIAGNOSTIC_CONTEXT_SCHEMA: Mapping[str, Mapping[str, Any]] = {
    "axis.missing-parameter": {"missing": tuple},
    "axis.size-mismatch": {"SI": (int, float), "N": int},
    "component.missing": {"expected": tuple, "missing": tuple},
    "acquisition.missing-parameter": {"missing": tuple},
}

_AXIS_PARAMETER_NAMES = frozenset({"OFFSET", "SF", "SW_p"})


def _validate_context_elements(code, context):
    """Validate the contents of a ``Diagnostic`` context.

    ``DIAGNOSTIC_CONTEXT_SCHEMA`` fixes the keys and the container types; this
    refines them to the elements the normative schema names, so that a
    ``context`` cannot carry an incoherent parameter name, component name or
    size.
    """
    if code == "axis.missing-parameter":
        names = context["missing"]
        if any(not isinstance(name, str) for name in names):
            raise ValueError(
                "diagnostic %r context['missing'] must name processing parameters, "
                "got %r" % (code, names)
            )
        unknown = [name for name in names if name not in _AXIS_PARAMETER_NAMES]
        if unknown:
            raise ValueError(
                "diagnostic %r context['missing'] must name processing parameters "
                "%s, got %s" % (code, sorted(_AXIS_PARAMETER_NAMES), sorted(unknown))
            )
    elif code == "axis.size-mismatch":
        for key in ("SI", "N"):
            value = context[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    "diagnostic %r context[%r] must be a real number, got %r"
                    % (code, key, value)
                )
        if context["N"] <= 0:
            raise ValueError(
                "diagnostic %r context['N'] must be positive, got %r"
                % (code, context["N"])
            )
    elif code == "component.missing":
        for key in ("expected", "missing"):
            names = context[key]
            if any(not isinstance(name, str) or not name for name in names):
                raise ValueError(
                    "diagnostic %r context[%r] must name non-empty components, "
                    "got %r" % (code, key, names)
                )
        if not set(context["missing"]) <= set(context["expected"]):
            raise ValueError(
                "diagnostic %r context['missing'] %r must be a subset of "
                "'expected' %r" % (code, context["missing"], context["expected"])
            )
    elif code == "acquisition.missing-parameter":
        if any(not isinstance(name, str) or not name for name in context["missing"]):
            raise ValueError(
                "diagnostic %r context['missing'] must name non-empty parameters, "
                "got %r" % (code, context["missing"])
            )


def _freeze_array(values: Any) -> np.ndarray:
    """Return ``values`` as a read-only ndarray, without copying when possible."""
    array = np.asarray(values)
    array.setflags(write=False)
    return array


def _readonly(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return a read-only top-level view of ``mapping``."""
    return MappingProxyType(dict(mapping))


@dataclass(frozen=True)
class Reference:
    """Reference information for a frequency axis.

    ``offset`` is strictly the Bruker ``procs['OFFSET']`` value (the ppm of the
    first data point), never the carrier ``car`` in Hz.
    """

    observation_frequency: float | None = None
    observation_frequency_unit: str | None = None
    offset: float | None = None
    offset_unit: str | None = None
    source: ReferenceSource = "unknown"


@dataclass(frozen=True)
class Axis:
    values: np.ndarray | None = None
    unit: str | None = None
    label: str | None = None
    domain: Domain = "unknown"
    direction: Direction = "unknown"
    reference: Reference | None = None

    def __post_init__(self):
        if self.values is not None:
            object.__setattr__(self, "values", _freeze_array(self.values))


@dataclass(frozen=True)
class Component:
    name: str
    data: np.ndarray

    def __post_init__(self):
        object.__setattr__(self, "data", _freeze_array(self.data))


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: Severity
    message: str
    context: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.severity not in ("info", "warning"):
            raise ValueError(
                "diagnostic severity must be 'info' or 'warning', got %r"
                % (self.severity,)
            )
        schema = DIAGNOSTIC_CONTEXT_SCHEMA.get(self.code)
        if schema is None:
            raise ValueError("unknown diagnostic code %r" % (self.code,))
        if set(self.context) != set(schema):
            raise ValueError(
                "diagnostic %r context keys must be %s, got %s"
                % (self.code, sorted(schema), sorted(self.context))
            )
        for key, expected in schema.items():
            if not isinstance(self.context[key], expected):
                raise ValueError(
                    "diagnostic %r context[%r] must be %r, got %r"
                    % (self.code, key, expected, self.context[key])
                )
        _validate_context_elements(self.code, self.context)
        object.__setattr__(self, "context", _readonly(self.context))


@dataclass(frozen=True)
class ReadResult:
    data: np.ndarray
    axes: tuple[Axis, ...]
    metadata: Mapping[str, Any]
    components: tuple[Component, ...]
    applied_corrections: Mapping[str, Any]
    diagnostics: tuple[Diagnostic, ...]
    format: str
    source: str | os.PathLike[str]
    domains: tuple[Domain, ...] = ()
    encoding: tuple[str, ...] = ()
    dimensions: Mapping[str, Any] = field(default_factory=dict)
    acquisition: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        object.__setattr__(self, "data", _freeze_array(self.data))
        object.__setattr__(self, "axes", tuple(self.axes))
        object.__setattr__(self, "metadata", _readonly(self.metadata))
        object.__setattr__(self, "components", tuple(self.components))
        object.__setattr__(
            self, "applied_corrections", _readonly(self.applied_corrections)
        )
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "domains", tuple(self.domains))
        object.__setattr__(self, "encoding", tuple(self.encoding))
        object.__setattr__(self, "dimensions", _readonly(self.dimensions))
        object.__setattr__(self, "acquisition", _readonly(self.acquisition))
