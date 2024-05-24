from persil import string


def test_skip():
    parser = string("test").skip(string("-"))
    assert parser.parse("test-") == "test"
