from importlib.metadata import EntryPoint, EntryPoints
from types import ModuleType

import pytest
from triton import backends


def plugin_module(name, base):
    module = ModuleType(name)
    concrete = type("Concrete", (base,), {method: lambda *args: None for method in base.__abstractmethods__})
    concrete.__module__ = name
    module.Concrete = concrete
    return module


@pytest.mark.parametrize("duplicate_name", [False, True])
def test_external_backend_selection_preserves_entrypoint_order(monkeypatch, duplicate_name):
    eps = EntryPoints([
        EntryPoint("first", "external.alpha", "triton.backends"),
        EntryPoint("unused", "missing.module", "unrelated"),
        EntryPoint("first" if duplicate_name else "second", "external.beta", "triton.backends"),
    ])
    modules = {
        f"external.{name}.{kind}": plugin_module(f"external.{name}.{kind}", base)
        for name in ["alpha", "beta"]
        for kind, base in [("compiler", backends.BaseBackend), ("driver", backends.DriverBase)]
    }
    imports = []

    def import_module(name):
        imports.append(name)
        return modules[name]

    monkeypatch.delenv("TRITON_BACKENDS_IN_TREE", raising=False)
    monkeypatch.setattr(backends, "entry_points", lambda **params: eps.select(**params))
    monkeypatch.setattr(backends.importlib, "import_module", import_module)
    result = backends._discover_backends()
    assert list(result) == (["first"] if duplicate_name else ["first", "second"])
    assert imports == [f"external.{name}.{kind}" for name in ["alpha", "beta"] for kind in ["compiler", "driver"]]
    final = result["first" if duplicate_name else "second"]
    assert final.compiler is modules["external.beta.compiler"].Concrete
    assert final.driver is modules["external.beta.driver"].Concrete


def test_external_backend_import_failure_propagates(monkeypatch):
    eps = EntryPoints([EntryPoint("missing", "external.missing", "triton.backends")])
    monkeypatch.delenv("TRITON_BACKENDS_IN_TREE", raising=False)
    monkeypatch.setattr(backends, "entry_points", lambda **params: eps.select(**params))

    def fail(name):
        raise ImportError("external plugin unavailable")

    monkeypatch.setattr(backends.importlib, "import_module", fail)
    with pytest.raises(ImportError, match="external plugin unavailable"):
        backends._discover_backends()
