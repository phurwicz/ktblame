import re
import json
from ktblame import KeySnippet
from collections import defaultdict


def extract_py_definitions(file_content):
    '''
    Extract function and class definitions from a Python file.
    Note that this function does not account for nested definitions.
    '''
    lines = file_content.split('\n')
    functions = dict()
    _key, _buffer, _line_indices = None, [], []
    for i, _line in enumerate(lines):
        # remove trailing newline characters to prevent duplicate newlines
        _line = _line.rstrip('\n')
        # a function definition starts with a decorator or a def
        # it also ends any previous definition
        _deco_match = re.match(r'^@[a-z_]+', _line)
        _def_match = re.match(r'(def|class)\ ([a-zA-Z0-9_]+)', _line)
        _unindented_match = re.match(r'^\S', _line)
        if _def_match or _deco_match or _unindented_match:
            if _key is not None:
                # drop trailing empty lines
                while _buffer and not _buffer[-1].strip():
                    _buffer.pop()
                    _line_indices.pop()
                # save the previous function definition
                _snippet = KeySnippet(
                    key=_key,
                    content='\n'.join(_buffer),
                    line_indices=_line_indices,
                )
                functions[_key] = _snippet
            _buffer.clear()
            _line_indices.clear()
            _key = None
            if _def_match:
                _key = _def_match.group(2)
        if (_deco_match or _def_match) or (not _unindented_match and _key is not None):
            _buffer.append(_line)
            _line_indices.append(i)
    
    if _buffer and _key is not None:
        _snippet = KeySnippet(
            key=_key,
            content='\n'.join(_buffer),
            line_indices=_line_indices,
        )
        functions[_key] = _snippet
    return functions


def get_keymapped_json_extractor(keymap_func=None):
    import json_source_map

    def extract_json(file_content):
        '''
        Extract JSON keys from a JSON file.
        '''
        lines = file_content.split('\n')
        json_dict = json.loads(file_content)
        source_map = json_source_map.calculate(file_content)
        key_snippets = dict()
        mapped_key_to_index_lines = defaultdict(list)

        for _k, _entry in source_map.items():
            if len(_k) == 0:
                continue
            _source_line_start = _entry.key_start.line if _entry.key_start is not None else _entry.value_start.line
            _source_line_end = _entry.value_end.line
            _nested_keys = [_ for _ in _k.split('/') if len(_) > 0]
            _sub_obj = json_dict
            for _nested_key in _nested_keys:
                if isinstance(_sub_obj, list):
                    _sub_obj = _sub_obj[int(_nested_key)]
                else:
                    _sub_obj = _sub_obj[_nested_key]

            _mapped_key = _k if keymap_func is None else keymap_func(_k, _sub_obj)
            _source_index_lines = zip(range(_source_line_start, _source_line_end + 1), lines[_source_line_start:(_source_line_end + 1)])
            mapped_key_to_index_lines[_mapped_key].extend(_source_index_lines)

        for _k, _index_lines in mapped_key_to_index_lines.items():
            _sorted_lines = sorted(_index_lines, key=lambda x: x[0])
            _content = '\n'.join([_[1] for _ in _sorted_lines])
            _line_indices = [_[0] for _ in _sorted_lines]
            key_snippets[_k] = KeySnippet(
                key=_k,
                content=_content,
                line_indices=_line_indices,
            )
        return key_snippets
    return extract_json
