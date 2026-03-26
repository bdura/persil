# Persil

Persil is a pure-python parsing library that draws much (most, let's be honest)
of its inspiration from the excellent [Parsy] library.

Hence the name, "Persil" ([pɛʁ.sil] or [pɛʁ.si]), the French word for parsley
-a most questionable pun on `Parsy -> Parsley -> Persil`, in case anyone missed it.

Like Parsy, Persil is a _"monadic parser combinator library for LL(infinity) grammars"_.
As a rough approximation, you can think of Persil as a typed "fork" of Parsy.
However, although the APIs are very similar, there are [notable differences](#compatibility-with-parsy)
that you might want to review if you're coming from Parsy.

If you're merely looking for a _somewhat_ type-aware version of Parsy,
you may be looking for `parsy-stubs`. Mypy can use it to infer most of the types,
but you'll find that shortcuts had to be taken in many cases.

## Getting started

Persil is a pure-Python library. You can install it with pip[^prefer-uv]:

```shell
pip install persil
```

Then, you can play with Persil much the same way you would with Parsy,
and enjoy the great developer experience that type-hinting brings to Persil.

### A basic example

```python
from persil import regex

year = regex(r"\d{4}").map(int)
```

This example should drive home the point that Persil is heavily inspired by Parsy.
The only difference in this particular case is type-safety: the Persil version
knows that `year` is a parser that expects a `str`, and outputs an `int`.

## Advanced use

### Parsing more complex object

Persil provides a "streaming" API to define more complex parsers.
This API is meant as a type-safe replacement for Parsy's [generate API][parsy-generate].

A motivating example:

```python
import datetime

from persil import from_stream, regex

year = regex("[0-9]{4}").map(int)
month = regex("(0[0-9]|1[0-2])").map(int)
day = regex("([012][0-9]|3[01])").map(int)

dash = string("-")

@from_stream
def date() -> datetime.date:
    """
    Parse a date in the format YYYY-MM-DD
    """
    y = stream(year)
    stream(dash)
    m = stream(month)
    stream(dash)
    d = stream(day)

    return datetime.date(y, m, d)
```

### Lazy definition

When you have self-referential parsers (for instance when parsing recursive structures),
you run into a problem: how do you reference a parser from within itself?

Persil's response to that problem is the `lazy` parser.

As a motivating example, let's say you want to parse a nested list of integers:

```
[-1, [0, 2], [], [[10, -42]]]
```

The following parser leverages the lazy API to allow parsing arbitrarily-nested
list of integers:

```python
from persil import regex, string
from persil import Parser
from persil import lazy

whitespace = regex(r"\s*")

lbrack = string("[")
rbrack = string("]")
comma = string(",")

number = regex(r"-?\d+").map(int)

type Value = int | list[Value]

@lazy
def array() -> Parser[str, list[Value]]:
    return lbrack >> value.sep_by(comma >> whitespace) << rbrack

value = cast(
    Parser[str, Value],
    number | array,
)
```

Using `lazy` enables breaking the dependency cycle between `array` and `value`,
by using a function to defer instantiating the parser until `value` is properly defined.

For a more involved example, see the [minimal JSON parser][json-example].

## Relation with Parsy

First of all, I am not affiliated in any way with the Parsy project.

### Rationale

Parsy's last commit is from a year ago at the time of writing. Moreover,
although the authors have started some development to propose a typed version
of their library, efforts in that area have stalled for two years.

### Compatibility with Parsy

Although Persil draws most of its inspiration from Parsy, maintaining a one-for-one
equivalence with the latter's API **is NOT among Persil's goal**.

For those coming from Parsy, here are some notable differences:

- the `Result` type is now a union between `Ok` and `Err`, which allows
  for a more type-safe API.
- `Err` is its own error: it inherits from `Exception` and can be raised.
- Persil introduces the `Stream` class, a wrapper around the input
  that can apply parsers sequentially, handling the book-keeping.
- the `generate` API has been removed

## Performance tips

Since Persil takes a functional approach, every transformation on a parser
produces a new parser. With that in mind, the way you define/use/combine
parsers may substantially affect performance.

Consider the following example:

```python
from datetime import datetime

from persil import Stream, from_stream, regex, string


@from_stream
def datetime_parser(stream: Stream[str]) -> datetime:
    year = stream.apply(regex(r"\d{4}").map(int))
    stream.apply(string("/"))
    month = stream.apply(regex(r"\d{2}").map(int))
    stream.apply(string("/"))
    day = stream.apply(regex(r"\d{2}").map(int))
    return datetime(year, month, day)
```

The resulting `datetime_parser` will re-create three new regex parsers
**every time** it is run.

A much better alternative:

```python
from datetime import datetime

from persil import Stream, from_stream, regex, string


year_parser = regex(r"\d{4}").map(int)
day_month_parser = regex(r"\d{2}").map(int)
slash_parser = string("/")

@from_stream
def datetime_parser(stream: Stream[str]) -> datetime:
    year = stream.apply(year_parser)
    stream.apply(slash_parser)
    month = stream.apply(day_month_parser)
    stream.apply(slash_parser)
    day = stream.apply(day_month_parser)
    return datetime(year, month, day)
```

That way, the lower-level parsers are only defined once.

[Parsy]: https://github.com/python-parsy/parsy
[parsy-generate]: https://parsy.readthedocs.io/en/latest/ref/generating.html#generating-a-parser

[json-example]: https://github.com/bdura/persil/blob/main/examples/json.py

[^prefer-uv]: You should really prefer a strict dependency manager like `uv`
