import re

from persil import Parser
from persil.result import Err, Ok, Result


def regex(
    exp: str | re.Pattern[str], flags=0, group: int | str | tuple = 0
) -> Parser[str, str]:
    """
    Returns a parser that expects the given ``exp``, and produces the
    matched string. ``exp`` can be a compiled regular expression, or a
    string which will be compiled with the given ``flags``.

    Optionally, accepts ``group``, which is passed to re.Match.group
    https://docs.python.org/3/library/re.html#re.Match.group> to
    return the text from a capturing group in the regex instead of the
    entire match.
    """

    if isinstance(exp, (str, bytes)):
        exp = re.compile(exp, flags)
    if isinstance(group, (str, int)):
        group = (group,)

    @Parser
    def regex_parser(stream, index: int) -> Result[str]:
        match = exp.match(stream, index)
        if match:
            return Ok(match.group(*group), match.end())
        else:
            return Err(index, [exp.pattern], stream)

    return regex_parser


def regex_groupdict(
    exp: str | re.Pattern[str], flags=0
) -> Parser[str, dict[str, str | None]]:
    if isinstance(exp, (str, bytes)):
        exp = re.compile(exp, flags)

    @Parser
    def regex_parser(stream: str, index: int) -> Result[dict[str, str | None]]:
        match = exp.match(stream, index)
        if match:
            return Ok(match.groupdict(), match.end())
        else:
            return Err(index, [exp.pattern], stream)

    return regex_parser
