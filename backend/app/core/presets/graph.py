"""The module dependency graph, enforced in code.

The preset schema documents that a module entry carries the modules it
requires. A schema that documents a rule is not the same thing as a
product that keeps it: this module is where the rule is kept.

Three things are refused:

* a module that is enabled while a module it requires is not enabled —
  the refusal names the missing dependency;
* a preset whose dependency edges form a cycle;
* a preset whose dependency edge names a module the preset does not
  define, or a module the product does not have.

The edges are the union of two sources. The product's own edges live in
:mod:`app.core.presets.modules` and a preset may not weaken them; a preset
may add an edge of its own. The union is what is enforced.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from app.core.errors import validation
from app.core.presets.modules import MODULES, available_modules


@dataclass(frozen=True)
class GraphProblem:
    """One way a dependency graph is broken."""

    reason: str
    module: str
    missing: tuple[str, ...] = ()
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "reason": self.reason,
            "module": self.module,
            "missing": list(self.missing),
            "detail": self.detail,
        }


class ModuleGraph:
    """A directed acyclic graph over module keys."""

    def __init__(self, edges: Mapping[str, Iterable[str]]) -> None:
        self._edges: dict[str, tuple[str, ...]] = {
            key: tuple(dict.fromkeys(str(item) for item in values))
            for key, values in edges.items()
        }

    # -- construction ------------------------------------------------------

    @classmethod
    def product_graph(cls) -> "ModuleGraph":
        """The graph the product enforces on its own, with no preset."""
        return cls({key: spec.requires for key, spec in MODULES.items()})

    @classmethod
    def for_preset(cls, preset) -> "ModuleGraph":
        """The effective graph of a preset: the product's edges plus its own."""
        edges: dict[str, tuple[str, ...]] = {}
        for entry in preset.module_entries:
            key = entry["key"]
            required = set(entry.get("requires") or ())
            spec = MODULES.get(key)
            if spec is not None:
                required |= set(spec.requires)
            edges[key] = tuple(sorted(required))
        return cls(edges)

    # -- inspection --------------------------------------------------------

    @property
    def modules(self) -> list[str]:
        return sorted(self._edges)

    def dependencies(self, module: str) -> tuple[str, ...]:
        """The modules a module requires, directly."""
        return self._edges.get(module, ())

    def transitive_dependencies(self, module: str) -> tuple[str, ...]:
        """Every module a module needs, directly or through another one."""
        seen: list[str] = []
        stack = list(self.dependencies(module))
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.append(current)
            stack.extend(self.dependencies(current))
        return tuple(sorted(seen))

    def find_cycle(self) -> list[str] | None:
        """The first cycle in the graph, or ``None`` when there is none.

        A cycle is a path ``a -> b -> a``: it means there is no order in
        which the modules could be switched on, so the graph cannot be
        satisfied at all.
        """
        visiting: list[str] = []
        done: set[str] = set()

        def walk(node: str) -> list[str] | None:
            if node in visiting:
                start = visiting.index(node)
                return visiting[start:] + [node]
            if node in done:
                return None
            visiting.append(node)
            for neighbour in sorted(self.dependencies(node)):
                found = walk(neighbour)
                if found is not None:
                    return found
            visiting.pop()
            done.add(node)
            return None

        for module in self.modules:
            found = walk(module)
            if found is not None:
                return found
        return None

    # -- checks ------------------------------------------------------------

    def problems(self, known_modules: Iterable[str] | None = None) -> list[GraphProblem]:
        """Every way this graph is broken, as the preset's own terms.

        ``known_modules`` is the set of modules the product serves. When it
        is not given, the modules the running application serves are used.
        """
        known = set(known_modules) if known_modules is not None else set(available_modules())
        found: list[GraphProblem] = []

        for module in self.modules:
            if module not in known:
                found.append(
                    GraphProblem(
                        reason="unknown_module",
                        module=module,
                        detail=(
                            f"the module {module} is not served by the application; "
                            "a preset may not offer it"
                        ),
                    )
                )
            for dependency in self.dependencies(module):
                if dependency not in known:
                    found.append(
                        GraphProblem(
                            reason="unknown_module",
                            module=module,
                            missing=(dependency,),
                            detail=(
                                f"the module {module} requires {dependency}, which "
                                "the application does not serve"
                            ),
                        )
                    )
                elif dependency not in self._edges:
                    found.append(
                        GraphProblem(
                            reason="unknown_dependency",
                            module=module,
                            missing=(dependency,),
                            detail=(
                                f"the module {module} requires {dependency}, which "
                                "the preset does not define"
                            ),
                        )
                    )

        cycle = self.find_cycle()
        if cycle is not None:
            found.append(
                GraphProblem(
                    reason="dependency_cycle",
                    module=cycle[0],
                    missing=tuple(cycle),
                    detail=(
                        "the dependency edges form a cycle: " + " -> ".join(cycle)
                    ),
                )
            )
        return found

    def unmet(self, enabled: Iterable[str]) -> list[GraphProblem]:
        """The enabled modules whose dependencies are not enabled."""
        on = set(enabled)
        found: list[GraphProblem] = []
        for module in sorted(on):
            missing = tuple(
                dependency
                for dependency in self.transitive_dependencies(module)
                if dependency not in on
            )
            if missing:
                found.append(
                    GraphProblem(
                        reason="dependency_not_enabled",
                        module=module,
                        missing=missing,
                        detail=(
                            f"the module {module} is enabled but "
                            + ", ".join(missing)
                            + (" is" if len(missing) == 1 else " are")
                            + " not enabled"
                        ),
                    )
                )
        return found


def check_module_enablement(
    enabled: Iterable[str],
    *,
    graph: ModuleGraph | None = None,
) -> None:
    """Refuse a configuration that enables a module without its dependencies.

    Raises :class:`app.core.errors.ApiError` with the code
    ``module_dependency_unmet`` and the missing dependency named in the
    details. The code is the one the shared error contract publishes for
    exactly this refusal.
    """
    effective = graph if graph is not None else ModuleGraph.product_graph()
    problems = effective.unmet(enabled)
    if not problems:
        return
    first = problems[0]
    raise validation(
        "module_dependency_unmet",
        first.detail,
        module=first.module,
        requires=list(first.missing),
    )


def module_dependencies_of(preset) -> dict[str, list[str]]:
    """The effective dependency edges of a preset, for the API."""
    graph = ModuleGraph.for_preset(preset)
    return {module: list(graph.dependencies(module)) for module in graph.modules}
