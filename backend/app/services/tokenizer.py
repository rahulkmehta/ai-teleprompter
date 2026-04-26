"""Tokenization feeding the alignment pipeline.

The script (once per session) and live transcripts (every Deepgram event) both
flow through this module so their token surfaces match exactly when the aligner
compares them. Each Token carries:

  - raw:       original form, preserved for the teleprompter display
  - norm:      lowercased, alphanumeric-only form used for matching
  - metaphone: phonetic code so alignment survives mispronunciations
  - idf:       inverse-rarity weight (via wordfreq) so common words don't
               dominate alignment scoring
"""
import re
from dataclasses import dataclass

import jellyfish
from wordfreq import zipf_frequency


WORD_REGEX = re.compile(r"[a-zA-Z0-9]+(?:'[a-zA-Z0-9]+)*")
SENTENCE_END_REGEX = re.compile(r"[.!?]+(?:\s+|$)")
MAX_ZIPF = 8.0
MIN_IDF = 0.1


@dataclass(frozen=True)
class Token:
    raw: str
    norm: str
    metaphone: str
    idf: float


@dataclass(frozen=True)
class TokenizedScript:
    tokens: tuple[Token, ...]
    sentences: tuple[tuple[int, int], ...]

    @property
    def normalized(self) -> list[str]:
        return [t.norm for t in self.tokens]

    @property
    def display(self) -> list[str]:
        return [t.raw for t in self.tokens]

    def __len__(self) -> int:
        return len(self.tokens)


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def metaphone(text: str) -> str:
    return jellyfish.metaphone(text) if text else ""


def compute_idf(norm: str) -> float:
    zipf = zipf_frequency(norm, "en")
    return max(MIN_IDF, 1.0 - zipf / MAX_ZIPF)


def _build_token(raw: str) -> Token | None:
    norm = normalize(raw)
    if not norm:
        return None
    return Token(raw=raw, norm=norm, metaphone=metaphone(norm), idf=compute_idf(norm))


def tokenize_script(text: str) -> TokenizedScript:
    tokens: list[Token] = []
    sentences: list[tuple[int, int]] = []
    for chunk in SENTENCE_END_REGEX.split(text.strip()):
        if not chunk.strip():
            continue
        start = len(tokens)
        for match in WORD_REGEX.finditer(chunk):
            tok = _build_token(match.group(0))
            if tok is not None:
                tokens.append(tok)
        if len(tokens) > start:
            sentences.append((start, len(tokens)))
    return TokenizedScript(tokens=tuple(tokens), sentences=tuple(sentences))


def tokenize_transcript(text: str) -> list[Token]:
    out: list[Token] = []
    for match in WORD_REGEX.finditer(text):
        tok = _build_token(match.group(0))
        if tok is not None:
            out.append(tok)
    return out


def find_sentence(idx: int, sentences: tuple[tuple[int, int], ...]) -> tuple[int, int]:
    for s, e in sentences:
        if s <= idx < e:
            return (s, e)
    return (idx, idx)
