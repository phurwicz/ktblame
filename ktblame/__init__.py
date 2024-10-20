import git
from tqdm import tqdm
from typing import List, Set
from collections import defaultdict
from pydantic import BaseModel


class KeySnippet(BaseModel):
    key: str
    content: str
    line_numbers: List[int]


class KeySnapshot(KeySnippet):
    hexsha: str
    file_path: str


class LineBlame(BaseModel):
    hexsha: str
    line: str


class FileBlame(BaseModel):
    file_path: str
    hexsha: str
    lineblames: List[LineBlame]
    changed_line_numbers: Set[int]


class KeyTimeBlame:
    '''Blame that narrows down to a specific key and traverses time.'''
    def __init__(self, repo_path):
        self.repo = git.Repo(repo_path)
        self.commits = dict()
        self.filehexsha_to_blame = dict()
        self.key_to_hexshas = defaultdict(set)
        # assumes that each key per hexsha only exists in one file
        self.keyhexsha_to_snapshot = dict()
        self.seen = set()

    def extract(self, file_path, kv_function):
        if file_path in self.seen:
            return

        commits = list(self.repo.iter_commits(paths=file_path))
        for _commit in tqdm(commits):
            self.commits[_commit.hexsha] = _commit

            # file-level processing
            _fileblame = self._extract_blame(file_path, _commit.hexsha)
            _lines = [_.line for _ in _fileblame.lineblames]
            _kv_dict = kv_function('\n'.join(_lines))

            # key-level processing
            for _k, _ksnippet in _kv_dict.items():
                _kcontent, _klinenumbers = _ksnippet.content, _ksnippet.line_numbers

                # detect if the key snippet had a change in this commit
                if not set(_klinenumbers).intersection(_fileblame.changed_line_numbers):
                    continue
                
                self.key_to_hexshas[_k].add(_commit.hexsha)
                
                _keyhexsha = f"{_k}@{_commit.hexsha}"
                assert _keyhexsha not in self.keyhexsha_to_snapshot, f"Key {_k} not unique at {_commit.hexsha}"
                self.keyhexsha_to_snapshot[_keyhexsha] = KeySnapshot(
                    key=_k,
                    content=_kcontent,
                    line_numbers=_klinenumbers,
                    hexsha=_commit.hexsha,
                    file_path=file_path,
                )

        self.seen.add(file_path)

    def _extract_blame(self, file_path, hexsha):
        blame = self.repo.blame(hexsha, file_path)
        lineblames, changed, line_number = [], set(), 0
        for _commit, _lines in blame:
            if _commit not in self.commits:
                self.commits[_commit.hexsha] = _commit
            if _commit.hexsha == hexsha:
                changed.update(range(line_number, line_number + len(_lines)))
            lineblames.extend([
                LineBlame(hexsha=_commit.hexsha, line=_line) for _line in _lines
            ])
            line_number += len(_lines)

        fileblame = FileBlame(
            file_path=file_path,
            hexsha=hexsha,
            lineblames=lineblames,
            changed_line_numbers=changed
        )
        filehexsha = f"{file_path}@{hexsha}"
        self.filehexsha_to_blame[filehexsha] = fileblame
        return fileblame

    def blame(self, key, hexsha):
        snapshot = self.keyhexsha_to_snapshot[f"{key}@{hexsha}"]
        file_path, line_numbers = snapshot.file_path, snapshot.line_numbers
        fileblame = self.filehexsha_to_blame[f"{file_path}@{hexsha}"]
        lines = [fileblame.lineblames[i] for i in line_numbers]
        return lines

    def relevant_hexshas(self, key):
        return sorted(self.key_to_hexshas[key], key=lambda h: self.commits[h].committed_datetime)
    

class StreamlitHelper:
    '''Helper class for interaction with streamlit widgets.'''
    import streamlit as st

    @st.cache_resource
    def load_blamer(repo_path):
        return KeyTimeBlame(repo_path)
    
    def commit_overview(commit):
        import streamlit as st
        col1, col2 = st.columns(2)
        with col1:
            st.text(f"{commit.author.name} @ {commit.hexsha[:10]}")
            st.write(commit.committed_datetime)
        with col2:
            st.caption(commit.message.strip())

    def format_commit(commit, ref_hexsha):
        blamed_change = '+' * 10 if commit.hexsha == ref_hexsha else commit.hexsha[:10]
        commit_str = f"{blamed_change:>10} |{commit.author.name[:10]:>10} @{commit.committed_datetime.strftime('%Y-%m-%d %H:%M')}"
        return commit_str

    @staticmethod
    def default_sidebar(kv_functions):
        import streamlit as st
        main_params = dict()
        with st.sidebar:
            repo_path = st.text_input("Repository path", value=".")
            blamer = StreamlitHelper.load_blamer(repo_path)
            main_params['blamer'] = blamer

            with st.form("submit"):
                file_path = st.text_input("File path", value="app.py")
                kv_func_key = st.selectbox("Extractor", kv_functions.keys())
                submitted = st.form_submit_button("Submit", type="primary")

                if submitted:
                    blamer.extract(file_path, kv_functions[kv_func_key])

            selected_key = st.selectbox("Key", list(blamer.key_to_hexshas.keys()))
            main_params['selected_key'] = selected_key
            hexshas = blamer.relevant_hexshas(selected_key)

            if hexshas:
                hexsha = st.select_slider("Commit", hexshas, format_func=lambda h: blamer.commits[h].committed_datetime.strftime('%Y-%m-%d %H:%M'))

                main_params['selected_commit'] = blamer.commits[hexsha]
                main_params['ready_flag'] = True
            else:
                main_params['ready_flag'] = False

        return main_params

    @staticmethod
    def default_main(kv_functions):
        import streamlit as st
        main_params = StreamlitHelper.default_sidebar(kv_functions)

        if not main_params['ready_flag']:
            return

        blamer = main_params['blamer']
        selected_key = main_params['selected_key']
        selected_commit = main_params['selected_commit']

        StreamlitHelper.commit_overview(selected_commit)
        display_lines = []
        for _blamedline in blamer.blame(selected_key, selected_commit.hexsha):
            _lastcommit = blamer.commits[_blamedline.hexsha]
            _display = f"{StreamlitHelper.format_commit(_lastcommit, selected_commit.hexsha)} |{_blamedline.line}"
            display_lines.append(_display)

        st.code('\n'.join(display_lines))

