import re
import streamlit as st
from ktblame import KeySnippet, StreamlitHelper


st.set_page_config(layout="wide")


@st.cache_data
def extract_function_definitions(file_content):
    '''Extract function definitions from a Python file.'''
    functions = dict()
    lines = file_content.split('\n')
    _key, _buffer = None, []
    for i, _line in enumerate(lines):
        _match = re.match(r'def\ ([a-z_]+)\(', _line)
        if _match:
            if _key is not None:
                _snippet = KeySnippet(
                    key=_key,
                    content='\n'.join(_buffer),
                    line_numbers=list(range(i - len(_buffer), i)),
                )
                functions[_key] = _snippet
            _buffer.clear()
            _key = _match.group(1)
        elif re.match(r'^[a-z_]', _line):
            _buffer.clear()
        _buffer.append(_line)
    
    if _buffer and _key is not None:
        _snippet = KeySnippet(
            key=_key,
            content='\n'.join(_buffer),
            line_numbers=list(range(i - len(_buffer), i + 1)),
        )
        functions[_key] = _snippet
    return functions



KV_FUNCTIONS = {
    _func.__name__: _func for _func in [
        extract_function_definitions
    ]
}


StreamlitHelper.default_main(KV_FUNCTIONS)