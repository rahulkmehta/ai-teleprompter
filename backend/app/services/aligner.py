from collections import deque
from dataclasses import dataclass, field
from typing import Literal

from rapidfuzz.distance import Levenshtein

from app.core.config import Settings
from app.services.tokenizer import (
    Token,
    TokenizedScript,
    find_sentence,
    tokenize_transcript,
)

GAP_PENALTY = -0.1
EXPECTED_AVG_IDF = 0.2

def score(t1: Token, t2: Token, config: Settings) -> float:
    s_exact = 1.0 if t1.norm == t2.norm else 0.0
    s_phonetic = 1.0 if t1.metaphone and t1.metaphone == t2.metaphone else 0.0
    max_len = max(len(t1.norm), len(t2.norm))
    s_lev = 1.0 - Levenshtein.distance(t1.norm, t2.norm) / max_len
    raw = (
        config.alpha_exact * s_exact
        + config.beta_phonetic * s_phonetic
        + config.gamma_levenshtein * s_lev
    )
    return raw * t2.idf


@dataclass(frozen=True)
class Match:
    pointer: int
    confidence: float


def align(
    buffer: list[Token],
    script: TokenizedScript,
    current_pointer: int,
    config: Settings,
    *,
    window_size: int | None = None,
) -> Match:
    size = window_size if window_size is not None else config.window_size
    window = script.tokens[current_pointer : current_pointer + size]
    if not buffer or not window:
        return Match(pointer=current_pointer, confidence=0.0)

    n = len(buffer)
    m = len(window)
    M = [[0.0] * (m + 1) for _ in range(n + 1)]

    best_score = 0.0
    best_j = 0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            match_s = M[i - 1][j - 1] + score(buffer[i - 1], window[j - 1], config)
            del_s = M[i - 1][j] + GAP_PENALTY
            ins_s = M[i][j - 1] + GAP_PENALTY
            M[i][j] = max(0.0, match_s, del_s, ins_s)
            if i == n and M[i][j] > best_score:
                best_score = M[i][j]
                best_j = j

    new_pointer = current_pointer + best_j
    confidence = min(1.0, best_score / max(1.0, n * EXPECTED_AVG_IDF))
    return Match(pointer=new_pointer, confidence=confidence)


@dataclass
class AlignmentResult:
    pointer: int
    confidence: float
    tentative: bool
    state: Literal["on_script", "off_script", "idle"]


@dataclass
class Aligner:
    script: TokenizedScript
    config: Settings
    committed_pointer: int = 0
    tentative_pointer: int = 0
    confidence: float = 0.0
    low_confidence_streak: int = 0
    final_tokens: deque[Token] = field(default_factory=lambda: deque(maxlen=64))
    interim_tokens: list[Token] = field(default_factory=list)

    def buffer(self) -> list[Token]:
        combined = list(self.final_tokens) + self.interim_tokens
        return combined[-self.config.buffer_size:]

    def _try_reanchor(self) -> Match | None:
        buf = self.buffer()
        if not buf:
            return None
        remaining = len(self.script) - self.committed_pointer
        if remaining <= 0:
            return None
        global_match = align(
            buf,
            self.script,
            self.committed_pointer,
            self.config,
            window_size=remaining,
        )
        if global_match.confidence >= self.config.re_anchor_confidence:
            return global_match
        return None

    def process(self, text: str, is_final: bool) -> AlignmentResult:
        new_tokens = tokenize_transcript(text)
        if is_final:
            self.final_tokens.extend(new_tokens)
            self.interim_tokens = []
        else:
            self.interim_tokens = new_tokens

        match = align(self.buffer(), self.script, self.tentative_pointer, self.config)
        new_pointer = self.tentative_pointer
        re_anchored = False

        if match.confidence >= self.config.confidence_floor:
            candidate = min(match.pointer, self.tentative_pointer + self.config.max_forward_jump)
            sentence_start, _ = find_sentence(self.committed_pointer, self.script.sentences)
            new_pointer = max(candidate, sentence_start)
            self.low_confidence_streak = 0
        else:
            self.low_confidence_streak += 1
            if self.low_confidence_streak >= self.config.re_anchor_streak:
                global_match = self._try_reanchor()
                if global_match is not None:
                    new_pointer = global_match.pointer
                    self.low_confidence_streak = 0
                    re_anchored = True

        if re_anchored:
            self.committed_pointer = new_pointer
            self.tentative_pointer = new_pointer
        else:
            if is_final:
                self.committed_pointer = max(self.committed_pointer, new_pointer)
            self.tentative_pointer = max(
                self.tentative_pointer, new_pointer, self.committed_pointer
            )
        self.confidence = match.confidence

        on_script = self.low_confidence_streak < self.config.re_anchor_streak
        return AlignmentResult(
            pointer=self.tentative_pointer,
            confidence=self.confidence,
            tentative=not is_final,
            state="on_script" if on_script else "off_script",
        )
