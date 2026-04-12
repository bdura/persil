import pytest
from hypothesis import given, strategies as st

from persil.result import Err, Ok, ParseError
from persil.utils import RowCol


def test_ok_returns_self():
    ok = Ok(42, 0)
    assert ok.ok() is ok


def test_err_ok_raises_parse_error():
    err = Err(0, frozenset({"thing"}), RowCol(0, 0, 0))
    with pytest.raises(ParseError):
        err.ok()


def test_err_str_single_expected():
    err = Err(0, frozenset({"integer"}), RowCol(0, 0, 0))
    assert str(err) == "expected integer at 0:0"


def test_err_str_multiple_expected():
    err = Err(0, frozenset({"integer", "string"}), RowCol(0, 0, 0))
    assert str(err) == "expected one of integer, string at 0:0"


def test_err_map_is_noop():
    err = Err(0, frozenset({"thing"}), RowCol(0, 0, 0))
    assert err.map(lambda x: x + 1) is err


def test_err_aggregate_keeps_further_error():
    # `other` is further into the stream than `self`, so `other` wins entirely.
    earlier = Err(3, frozenset({"b"}), RowCol(3, 0, 3))
    further = Err(5, frozenset({"a"}), RowCol(5, 0, 5))
    result = earlier.aggregate(further)

    assert isinstance(result, Err)
    assert result.index == 5
    assert result.location == RowCol(5, 0, 5)
    # Only the furthest error's expectations are kept.
    assert result.expected == frozenset({"a"})


def test_err_aggregate_merges_at_same_index():
    err_a = Err(5, frozenset({"a"}), RowCol(5, 0, 5))
    err_b = Err(5, frozenset({"b"}), RowCol(5, 0, 5))
    result = err_a.aggregate(err_b)

    assert isinstance(result, Err)
    assert result.index == 5
    assert result.expected == frozenset({"a", "b"})


def test_err_aggregate_with_ok_returns_ok():
    err = Err(0, frozenset({"a"}), RowCol(0, 0, 0))
    ok = Ok(42, 5)
    result = err.aggregate(ok)
    assert isinstance(result, Ok)
    assert result.value == 42


def test_parse_error_exposes_err_attributes():
    err = Err(3, frozenset({"x"}), RowCol(3, 1, 0))
    exc = ParseError(err)
    assert exc.index == 3
    assert exc.expected == frozenset({"x"})
    assert exc.location == RowCol(3, 1, 0)
    assert "expected x at 1:0" in str(exc)


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


def test_err_from_stream_non_text_sequence():
    """For non-str/bytes sequences, location falls back to the raw index."""
    err = Err.from_stream(2, "thing", [1, 2, 3])
    assert err.location == 2
    assert err.expected == frozenset({"thing"})


@given(
    idx_a=st.integers(min_value=0, max_value=1000),
    idx_b=st.integers(min_value=0, max_value=1000),
)
def test_aggregate_keeps_furthest_index(idx_a: int, idx_b: int):
    """aggregate always picks the error furthest into the stream."""
    err_a = Err(idx_a, frozenset({"a"}), idx_a)
    err_b = Err(idx_b, frozenset({"b"}), idx_b)
    result = err_a.aggregate(err_b)

    assert isinstance(result, Err)
    assert result.index == max(idx_a, idx_b)
    if idx_a == idx_b:
        assert result.expected == frozenset({"a", "b"})
    elif idx_a > idx_b:
        assert result.expected == frozenset({"a"})
    else:
        assert result.expected == frozenset({"b"})
