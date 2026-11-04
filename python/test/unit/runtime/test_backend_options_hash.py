"""Frozen backend options retain the standard dataclass field-tuple hash."""

from dataclasses import fields, replace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from triton.backends.amd.compiler import HIPOptions
from triton.backends.nvidia.compiler import CUDAOptions


@pytest.mark.parametrize("options_type", [HIPOptions, CUDAOptions])
@given(st.data())
def test_backend_options_hash_matches_dataclass_fields(options_type, data):
    value = object.__new__(options_type)
    hashed_fields = [field for field in fields(options_type) if (field.compare if field.hash is None else field.hash)]
    values = data.draw(
        st.lists(
            st.integers() | st.text() | st.binary() | st.none(),
            min_size=len(hashed_fields),
            max_size=len(hashed_fields),
        )
    )
    for field, item in zip(hashed_fields, values):
        object.__setattr__(value, field.name, item)
    assert hash(value) == hash(tuple(getattr(value, field.name) for field in hashed_fields))


@pytest.mark.parametrize("options_type", [HIPOptions, CUDAOptions])
def test_backend_options_hash_rejects_each_unhashable_field(options_type):
    hashed_fields = [field for field in fields(options_type) if (field.compare if field.hash is None else field.hash)]
    for unhashable in hashed_fields:
        value = object.__new__(options_type)
        for index, field in enumerate(hashed_fields):
            object.__setattr__(value, field.name, [] if field.name == unhashable.name else index)
        with pytest.raises(TypeError, match="unhashable type: 'list'"):
            hash(value)


@pytest.mark.parametrize("options_type,arch", [(HIPOptions, "gfx942"), (CUDAOptions, "sm_80")])
def test_backend_options_constructed_replaced_and_subclass_hash(options_type, arch):
    original = options_type(arch=arch)
    replacement = replace(original, num_warps=8)
    for value in (original, replacement):
        assert hash(value) == hash(tuple(getattr(value, field.name) for field in fields(value)))
    subclass = type("OptionsSubclass", (options_type,), {})
    value = subclass(arch=arch)
    before = hash(value)
    object.__setattr__(value, "extra", [])
    assert hash(value) == before
