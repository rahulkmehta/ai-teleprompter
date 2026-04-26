import pytest
from app.core.config import Settings
from app.services.aligner import Aligner, align, score
from app.services.tokenizer import tokenize_script, tokenize_transcript

SCRIPT = (
    "The quick brown fox jumps over the lazy dog. "
    "Subterranean rivers flow beneath the mountain. "
    "Quantum mechanics describes the behavior of particles."
)

LONG_SCRIPT = (
    "The quick brown fox jumps over the lazy dog. "
    "She sells seashells by the seashore. "
    "Peter piper picked a peck of pickled peppers. "
    "How much wood would a woodchuck chuck. "
    "The rain in Spain falls mainly on the plain. "
    "Subterranean rivers flow beneath the ancient mountain ranges. "
    "Quantum mechanics describes the strange behavior of subatomic particles."
)


@pytest.fixture
def config() -> Settings:
    return Settings()


@pytest.fixture
def aligner(config: Settings) -> Aligner:
    return Aligner(script=tokenize_script(SCRIPT), config=config)


def test_score_exact_rare_match_is_significant(config: Settings):
    a = tokenize_transcript("subterranean")[0]
    b = tokenize_transcript("subterranean")[0]
    assert score(a, b, config) > 0.4


def test_score_phonetic_match_helps_substitution(config: Settings):
    a = tokenize_transcript("kafe")[0]
    b = tokenize_transcript("cafe")[0]
    assert score(a, b, config) > 0.1


def test_score_idf_makes_rare_outweigh_common(config: Settings):
    common = tokenize_transcript("the")[0]
    rare = tokenize_transcript("subterranean")[0]
    assert score(rare, rare, config) > score(common, common, config)


def test_score_unrelated_tokens_low(config: Settings):
    a = tokenize_transcript("quantum")[0]
    b = tokenize_transcript("dog")[0]
    assert score(a, b, config) < 0.3


def test_align_perfect_read_advances_to_end_of_buffer(config: Settings):
    script = tokenize_script("The quick brown fox jumps over the lazy dog.")
    buf = tokenize_transcript("The quick brown fox")
    match = align(buf, script, 0, config)
    assert match.pointer == 4
    assert match.confidence >= config.confidence_floor


def test_align_skipped_words_jumps_forward(config: Settings):
    script = tokenize_script("The quick brown fox jumps over the lazy dog.")
    buf = tokenize_transcript("lazy dog")
    match = align(buf, script, 0, config)
    assert match.pointer >= 8
    assert match.confidence >= config.confidence_floor


def test_align_garbage_yields_low_confidence(config: Settings):
    script = tokenize_script("The quick brown fox jumps over the lazy dog.")
    buf = tokenize_transcript("xyzznoword qrtablebla wxyzpdq")
    match = align(buf, script, 0, config)
    assert match.confidence < config.confidence_floor


def test_align_empty_buffer_no_movement(config: Settings):
    script = tokenize_script("Hello world.")
    match = align([], script, 0, config)
    assert match.pointer == 0
    assert match.confidence == 0.0


def test_aligner_perfect_read_advances(aligner: Aligner):
    aligner.process("The quick brown fox", is_final=True)
    assert aligner.committed_pointer >= 3


def test_aligner_ad_lib_holds_pointer(aligner: Aligner):
    aligner.process("The quick brown fox", is_final=True)
    p1 = aligner.committed_pointer
    aligner.process("um like so anyway", is_final=True)
    assert aligner.committed_pointer - p1 <= 1


def test_aligner_mispronunciation_still_advances(aligner: Aligner):
    aligner.process("The quick brown fox jumps over the lazy dog.", is_final=True)
    p1 = aligner.committed_pointer
    aligner.process("subterrayneean rivers flow", is_final=True)
    assert aligner.committed_pointer > p1


def test_aligner_skipped_sentence_advances_via_forward_alignment(aligner: Aligner):
    aligner.process("the quick brown fox", is_final=True)
    p1 = aligner.committed_pointer
    aligner.process("subterranean rivers flow beneath", is_final=True)
    assert aligner.committed_pointer > p1


def test_aligner_forward_jump_capped(aligner: Aligner):
    p_start = aligner.committed_pointer
    aligner.process("subterranean", is_final=True)
    assert aligner.committed_pointer - p_start <= aligner.config.max_forward_jump + 1


def test_aligner_state_off_script_under_garbage(aligner: Aligner):
    result = None
    for _ in range(6):
        result = aligner.process("hmm uhh okay", is_final=True)
    assert result is not None
    assert result.state == "off_script"


def test_aligner_off_script_then_reanchor_jumps(config: Settings):
    aligner = Aligner(script=tokenize_script(LONG_SCRIPT), config=config)
    for _ in range(6):
        aligner.process("hmm uhh", is_final=True)
    aligner.process("quantum mechanics subatomic particles", is_final=True)
    assert aligner.committed_pointer >= 40


def test_aligner_interim_does_not_commit(aligner: Aligner):
    aligner.process("The quick brown fox", is_final=False)
    assert aligner.committed_pointer == 0
    assert aligner.tentative_pointer >= 3


def test_aligner_final_after_interim_commits(aligner: Aligner):
    aligner.process("The quick", is_final=False)
    aligner.process("The quick brown fox", is_final=True)
    assert aligner.committed_pointer >= 3
