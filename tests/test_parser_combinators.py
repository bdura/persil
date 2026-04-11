import pytest
from hypothesis import assume, given, strategies as st

from persil import regex, string
from persil.parser import eof
from persil.result import Err


any_char = regex(r"[\s\S]")


def test_cut_success():
    parser = string("a").cut()
    assert parser.parse("a") == "a"


def test_cut_raises_on_failure():
    parser = string("a").cut()
    with pytest.raises(Err):
        parser.parse("b")


@given(text=st.text(alphabet="a", min_size=1, max_size=1))
def test_cut_is_transparent_on_success(text: str):
    """cut() must not alter the value or consumed length on success."""
    base = string("a")
    assert base.cut().parse(text) == base.parse(text)


def test_skip_second_fails():
    parser = string("a").skip(string("b"))
    with pytest.raises(Err):
        parser.parse("ac")


def test_combine_second_fails():
    parser = string("a").combine(string("b"))
    with pytest.raises(Err):
        parser.parse("ac")


def test_and_operator():
    parser = string("a") & string("b")
    assert parser.parse("ab") == ("a", "b")


def test_at_most():
    parser = string("a").at_most(3)
    assert parser.parse("aa") == ["a", "a"]


def test_at_least():
    parser = string("a").at_least(2)
    result, _ = parser.parse_partial("aaab")
    assert len(result) >= 2


@given(
    count=st.integers(min_value=0, max_value=20),
    limit=st.integers(min_value=0, max_value=20),
)
def test_at_most_bounds(count: int, limit: int):
    """at_most(n) always produces a list with len <= n."""
    text = "a" * count
    parser = string("a").at_most(limit)
    result, _ = parser.parse_partial(text)
    assert len(result) <= limit


def test_optional_match():
    parser = string("a").optional("default")
    assert parser.parse("a") == "a"


def test_optional_no_match():
    parser = string("a").optional("default")
    # `optional` alone doesn't consume EOF, so use parse_partial.
    result, _ = parser.parse_partial("b")
    assert result == "default"


@given(text=st.text(min_size=0, max_size=100))
def test_optional_never_raises(text: str):
    """optional() always succeeds — it either matches or returns the default."""
    parser = string("hello").optional("fallback")
    result, _ = parser.parse_partial(text)
    assert result in (text[:5], "fallback")
    if text.startswith("hello"):
        assert result == "hello"
    else:
        assert result == "fallback"


def test_sep_by_max_zero():
    parser = string("a").sep_by(string(","), max=0)
    result, _ = parser.parse_partial("a,b")
    assert result == []


def test_should_fail_when_inner_succeeds():
    parser = string("a").should_fail("not 'a'")
    with pytest.raises(Err):
        parser.parse("a")


def test_should_fail_when_inner_fails():
    # Inner parser fails → should_fail succeeds (consuming nothing).
    parser = string("a").should_fail("not 'a'")
    result, remainder = parser.parse_partial("b")
    assert isinstance(result, Err)
    assert remainder == "b"


@given(text=st.text(min_size=1, max_size=50))
def test_should_fail_inverts_success(text: str):
    """should_fail succeeds exactly when the inner parser fails, and vice versa."""
    inner = string("x")
    negated = inner.should_fail("not x")

    inner_ok = not isinstance(inner(text, 0), Err)
    negated_ok = not isinstance(negated(text, 0), Err)

    assert inner_ok != negated_ok, "exactly one of inner / negated should succeed"


def test_span_failure():
    parser = string("a").span()
    with pytest.raises(Err):
        parser.parse("b")


def test_add_second_fails():
    parser = string("a").times(1) + string("b").times(1)
    with pytest.raises(Err):
        parser.parse("ac")


@given(
    n=st.integers(min_value=0, max_value=10),
    m=st.integers(min_value=0, max_value=10),
)
def test_add_concatenates_lists(n: int, m: int):
    """times(n) + times(m) produces a list of exactly n + m items."""
    text = "a" * (n + m)
    parser = string("a").times(n) + string("a").times(m)
    result = parser.parse(text)
    assert result == ["a"] * (n + m)


def test_eof_not_at_end():
    with pytest.raises(Err):
        eof().parse_partial("leftover")


@given(n=st.integers(min_value=0, max_value=1000))
def test_map_functor_composition(n: int):
    """p.map(f).map(g) must equal p.map(lambda x: g(f(x)))."""
    text = str(n)
    base = regex(r"\d+")

    f = int
    g = lambda x: x * 2  # noqa: E731

    left = base.map(f).map(g).parse(text)
    right = base.map(lambda x: g(f(x))).parse(text)
    assert left == right


@given(
    count=st.integers(min_value=0, max_value=10),
    min_val=st.integers(min_value=0, max_value=5),
    max_val=st.integers(min_value=5, max_value=15),
)
def test_sep_by_result_length(count: int, min_val: int, max_val: int):
    """sep_by(min=m, max=n) result length is between m and n when it succeeds."""
    assume(min_val <= max_val)
    text = ",".join(["a"] * count) if count > 0 else ""
    parser = string("a").sep_by(string(","), min=min_val, max=max_val)

    try:
        result, _ = parser.parse_partial(text)
        assert min_val <= len(result) <= max_val
    except Err:
        # Expected when count < min_val.
        assert count < min_val
