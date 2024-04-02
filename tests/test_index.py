from persil import index, string


def test_index():
    parser = string("test") >> index
    assert parser.parse("test") == 4
