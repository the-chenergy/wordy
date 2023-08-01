from __future__ import annotations

import pathlib, random


def parse_word_list(file_path: pathlib.Path,
                    limit: int | None = None) -> list[str]:
    with open(file_path, 'r') as f:
        words = map(str.strip, f.readlines())
    words = filter(bool, words)
    words = map(str.lower, words)
    words = list(words)
    assert limit is None or limit > 0
    if limit is not None and limit < len(words): words = words[:limit]
    for i in range(1, len(words)):
        assert len(words[i]) == len(words[0])
    return words
