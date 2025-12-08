from hypothesis import given, strategies as st

from persil import regex

whitespace = regex(r"\s*")
word = regex(r"\w*").span()

parser = whitespace >> word


@given(
    newlines=st.text(alphabet="\n", min_size=0, max_size=1_000),
    ws=st.text(alphabet=" \t", min_size=0, max_size=1_000),
    word=st.text(alphabet="abcdefghij", min_size=0, max_size=1_000),
)
def test_string_parser(
    newlines: str,
    ws: str,
    word: str,
):
    text = newlines + ws + word

    span = parser.parse(text)

    start = span.start
    stop = span.stop

    assert start.index == len(newlines) + len(ws)
    assert start.row == len(newlines)
    assert start.col == len(ws)

    assert stop.index == len(newlines) + len(ws) + len(word)
    assert stop.row == len(newlines)
    assert stop.col == len(ws) + len(word)
