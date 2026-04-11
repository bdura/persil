import pytest
from hypothesis import given, strategies as st

from persil.result import Err, Ok


def test_ok_or_raise_returns_self():
    ok = Ok(42, 0)
    assert ok.ok_or_raise() is ok


def test_err_ok_or_raise_raises():
    err = Err(0, ["thing"], "0:0")
    with pytest.raises(Err):
        err.ok_or_raise()


def test_err_str_single_expected():
    err = Err(0, ["integer"], "0:0")
    assert str(err) == "expected integer at 0:0"


def test_err_str_multiple_expected():
    err = Err(0, ["integer", "string"], "0:0")
    assert str(err) == "expected one of integer, string at 0:0"


def test_err_map_is_noop():
    err = Err(0, ["thing"], "0:0")
    assert err.map(lambda x: x + 1) is err


def test_err_aggregate_keeps_further_error():
    # `other` is further into the stream than `self`, so `other`'s
    # location should be used.
    earlier = Err(5, ["a"], "0:5")
    further = Err(3, ["b"], "0:3")
    result = further.aggregate(earlier)

    assert isinstance(result, Err)
    assert result.index == 5
    assert result.location == "0:5"
    assert set(result.expected) == {"a", "b"}


def test_err_aggregate_with_ok_returns_ok():
    err = Err(0, ["a"], "0:0")
    ok = Ok(42, 5)
    result = err.aggregate(ok)
    assert isinstance(result, Ok)
    assert result.value == 42


@given(
    value=st.integers(),
    index=st.integers(min_value=0),
)
def test_ok_map_identity(value: int, index: int):
    """Functor identity law: ok.map(id) returns an equal Ok."""
    ok = Ok(value, index)
    mapped = ok.map(lambda x: x)
    assert mapped.value == ok.value
    assert mapped.index == ok.index


@given(
    value=st.integers(),
    index=st.integers(min_value=0),
)
def test_ok_map_composition(value: int, index: int):
    """Functor composition law: ok.map(f).map(g) == ok.map(g . f)."""
    f = lambda x: x + 1  # noqa: E731
    g = lambda x: x * 3  # noqa: E731

    ok = Ok(value, index)
    left = ok.map(f).map(g)
    right = ok.map(lambda x: g(f(x)))
    assert left.value == right.value
    assert left.index == right.index


@given(
    idx_a=st.integers(min_value=0, max_value=1000),
    idx_b=st.integers(min_value=0, max_value=1000),
)
def test_aggregate_keeps_furthest_index(idx_a: int, idx_b: int):
    """aggregate always picks the error furthest into the stream."""
    err_a = Err(idx_a, ["a"], f"0:{idx_a}")
    err_b = Err(idx_b, ["b"], f"0:{idx_b}")
    result = err_a.aggregate(err_b)

    assert isinstance(result, Err)
    assert result.index == max(idx_a, idx_b)
    assert set(result.expected) == {"a", "b"}
