import streamlit as st
from ktblame.builtin.extractors import extract_py_definitions
from ktblame.builtin.streamlit import StreamlitHelper


st.set_page_config(layout="wide")


KV_FUNCTIONS = {
    _func.__name__: st.cache_data(_func) for _func in [
        extract_py_definitions
    ]
}


StreamlitHelper.default_main(KV_FUNCTIONS)
