import git
from tqdm import tqdm
from typing import List, Set
from collections import defaultdict
from pydantic import BaseModel


class KeySnippet(BaseModel):
    key: str
    content: str
    line_indices: List[int]


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
    changed_line_indices: Set[int]


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
        for _commit in tqdm(commits, desc=f"KeyTimeBlame: extracting {file_path}"):
            self.commits[_commit.hexsha] = _commit

            # file-level processing
            _fileblame = self._extract_blame(file_path, _commit.hexsha)
            _lines = [_.line for _ in _fileblame.lineblames]
            _kv_dict = kv_function('\n'.join(_lines))

            # key-level processing
            for _k, _ksnippet in _kv_dict.items():
                _kcontent, _klinenumbers = _ksnippet.content, _ksnippet.line_indices

                # detect if the key snippet had a change in this commit
                if not set(_klinenumbers).intersection(_fileblame.changed_line_indices):
                    continue
                
                self.key_to_hexshas[_k].add(_commit.hexsha)
                
                _keyhexsha = f"{_k}@{_commit.hexsha}"
                assert _keyhexsha not in self.keyhexsha_to_snapshot, f"Key {_k} not unique at {_commit.hexsha}"
                self.keyhexsha_to_snapshot[_keyhexsha] = KeySnapshot(
                    key=_k,
                    content=_kcontent,
                    line_indices=_klinenumbers,
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
            changed_line_indices=changed
        )
        filehexsha = f"{file_path}@{hexsha}"
        self.filehexsha_to_blame[filehexsha] = fileblame
        return fileblame

    def blame(self, key, hexsha):
        snapshot = self.keyhexsha_to_snapshot[f"{key}@{hexsha}"]
        file_path, line_indices = snapshot.file_path, snapshot.line_indices
        fileblame = self.filehexsha_to_blame[f"{file_path}@{hexsha}"]
        lines = [fileblame.lineblames[i] for i in line_indices]
        return lines

    def relevant_hexshas(self, key):
        return sorted(self.key_to_hexshas[key], key=lambda h: self.commits[h].committed_datetime)