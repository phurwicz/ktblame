import re
import streamlit as st
from ktblame import KeySnippet, StreamlitHelper


st.set_page_config(layout="wide")


@st.cache_data
def extract_function_definitions(file_content):
    '''
    Extract function definitions from a Python file.
    Note that this function does not account for nested definitions.
    '''
    functions = dict()
    lines = file_content.split('\n')
    _key, _buffer, _line_numbers = None, [], []
    for i, _line in enumerate(lines):
        # a function definition starts with a decorator or a def
        # it also ends any previous definition
        _deco_match = re.match(r'^@[a-z_]+', _line)
        _def_match = re.match(r'def\ ([a-z_]+)\(', _line)
        _unindented_match = re.match(r'^\S', _line)
        if _def_match or _deco_match or _unindented_match:
            if _key is not None:
                _snippet = KeySnippet(
                    key=_key,
                    content='\n'.join(_buffer),
                    line_numbers=_line_numbers,
                )
                functions[_key] = _snippet
            _buffer.clear()
            _line_numbers.clear()
            _key = None
            if _def_match:
                _key = _def_match.group(1)
        if (_deco_match or _def_match) or (not _unindented_match and _key is not None):
            _buffer.append(_line)
            _line_numbers.append(i)
    
    if _buffer and _key is not None:
        _snippet = KeySnippet(
            key=_key,
            content='\n'.join(_buffer),
            line_numbers=_line_numbers,
        )
        functions[_key] = _snippet
    return functions



KV_FUNCTIONS = {
    _func.__name__: _func for _func in [
        extract_function_definitions
    ]
}


StreamlitHelper.default_main(KV_FUNCTIONS)
