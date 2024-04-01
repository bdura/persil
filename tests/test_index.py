from persil.parsers import index, string, tag


def test_index():
    parser = string("test") >> index
    assert parser.parse("test") == 4


def test_incompatible():
    parser = string("test") >> tag(b"test")