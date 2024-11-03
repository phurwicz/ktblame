import streamlit as st
from .. import KeyTimeBlame


class StreamlitHelper:
    '''Helper class for interaction with streamlit widgets.'''

    @st.cache_resource
    def load_blamer(repo_path):
        return KeyTimeBlame(repo_path)
    
    def commit_overview(commit):
        col1, col2 = st.columns(2)
        with col1:
            st.text(f"{commit.author.name} @ {commit.hexsha[:10]}")
            st.write(commit.committed_datetime)
        with col2:
            st.caption(commit.message.strip())

    def format_commit(commit, ref_hexsha):
        blamed_change = '+' * 7 if commit.hexsha == ref_hexsha else commit.hexsha[:7]
        commit_str = f"{blamed_change:>7} |{commit.author.name[:10]:>10} @{commit.committed_datetime.strftime('%Y-%m-%d')}"
        return commit_str

    @staticmethod
    def default_sidebar(kv_functions):
        main_params = dict()
        with st.sidebar:
            repo_path = st.text_input("Repository path", value="./")
            blamer = StreamlitHelper.load_blamer(repo_path)
            main_params['blamer'] = blamer

            with st.form("submit"):
                file_path = st.text_input("File path", value="example-streamlit-app.py")
                kv_func_key = st.selectbox("Extractor", kv_functions.keys())
                submitted = st.form_submit_button("Submit", type="primary")

                if submitted:
                    blamer.extract(file_path, kv_functions[kv_func_key])

            if blamer.key_to_hexshas:
                selected_key = st.selectbox("Key", list(blamer.key_to_hexshas.keys()), format_func=lambda k: f"({len(blamer.key_to_hexshas[k])}) {k}")
                main_params['selected_key'] = selected_key
                hexshas = blamer.relevant_hexshas(selected_key)
            else:
                hexshas = []

            if len(hexshas) >= 2:
                hexsha = st.select_slider("Commit", hexshas, format_func=lambda h: blamer.commits[h].committed_datetime.strftime('%Y-%m-%d %H:%M'))
                main_params['selected_commit'] = blamer.commits[hexsha]
                main_params['ready_flag'] = True
            elif len(hexshas) == 1:
                st.caption("Only one commit available.")
                main_params['selected_commit'] = blamer.commits[hexshas[0]]
                main_params['ready_flag'] = True
            else:
                main_params['ready_flag'] = False

        return main_params

    @staticmethod
    def default_main(kv_functions):
        main_params = StreamlitHelper.default_sidebar(kv_functions)

        if not main_params['ready_flag']:
            st.caption("No commit available. Please check the options in the sidebar.")
            return

        blamer = main_params['blamer']
        selected_key = main_params['selected_key']
        selected_commit = main_params['selected_commit']

        StreamlitHelper.commit_overview(selected_commit)
        display_lines, prev_commit, filler_length = [], None, 0
        for _blamedline in blamer.blame(selected_key, selected_commit.hexsha):
            _linecommit = blamer.commits[_blamedline.hexsha]
            if _linecommit != prev_commit:
                _linedesc = StreamlitHelper.format_commit(_linecommit, selected_commit.hexsha)
                prev_commit, filler_length = _linecommit, len(_linedesc)
            else:
                _linedesc = ' ' * filler_length
            _display = f"{_linedesc}|{_blamedline.line}"
            display_lines.append(_display)

        st.code('\n'.join(display_lines), line_numbers=True)
