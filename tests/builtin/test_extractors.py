import inspect
import json
from ktblame.builtin.extractors import extract_py_definitions, get_keymapped_json_extractor
from ktblame import KeySnippet, KeySnapshot, LineBlame, FileBlame, KeyTimeBlame


def test_extract_py_definitions():
    with open('ktblame/__init__.py', 'r') as f:
        content = f.read()

    functions = extract_py_definitions(content)

    for _expected_class in [
        KeySnippet,
        KeySnapshot,
        LineBlame,
        FileBlame,
        KeyTimeBlame,
    ]:
        _expected_class_name = _expected_class.__name__
        assert _expected_class_name in functions, f"{functions.keys()}"
        _keysnippet = functions[_expected_class_name]
        assert _keysnippet.key == _expected_class_name
        # left-hand side is 0-indexed, right-hand side is 1-indexed
        assert _keysnippet.line_indices[0] == inspect.getsourcelines(_expected_class)[1] - 1
        assert _keysnippet.content.strip() == inspect.getsource(_expected_class).strip()


def test_extract_json_default():
    extractor = get_keymapped_json_extractor()
    dummy_dict = dict(foo='bar', bar='baz')
    dummy_json = json.dumps(dummy_dict, indent=2)

    key_snippets = extractor(dummy_json)
    for _k, _v in dummy_dict.items():
        _path_k = f'/{_k}'
        assert _path_k in key_snippets
        assert _v in key_snippets[_path_k].content