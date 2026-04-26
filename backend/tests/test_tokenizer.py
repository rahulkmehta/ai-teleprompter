"""Unit tests for the tokenizer                                                                                                                                                                                             
                                                                                                                                                                                                                                        
Basically, we want to make sure the script and transcript pipelines                                                                                                                                                           
produce identical token surfaces. Otherwise, the aligner will get all messed up.                                                                                                                                                                 
"""                                                                                                                                                                                                                                     
import pytest                                                                                                                                                                                                                             
                                                                                                                                                                                                                                        
from app.services.tokenizer import (                                                                                                                                                                                                      
    MIN_IDF,                                                                                                                                                                                                                              
    compute_idf,                                                                                                                                                                                                                          
    find_sentence,                                                                                                                                                                                                                        
    metaphone,                                                                                                                                                                                                                          
    normalize,                                                                                                                                                                                                                            
    tokenize_script,                                                                                                                                                                                                                      
    tokenize_transcript,                
)                                                                                                                                                                                                                                         
                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                        
def test_normalize_basic():                                                                                                                                                                                                               
    assert normalize("Hello,") == "hello"                                                                                                                                                                                               
    assert normalize("don't") == "dont"
    assert normalize("$500") == "500"       
                                        
                                                    
def test_normalize_strips_non_ascii():                                                                                                                                                                                                    
    assert normalize("Café!") == "caf"
                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                        
def test_metaphone_phonetic_equivalence():
    assert metaphone("kafe") == metaphone("cafe")  
    assert metaphone("there") == metaphone("their")    
                                
                                                                                                                                                                                                                                        
def test_compute_idf_common_words_clamped_to_floor():
    assert compute_idf("the") == pytest.approx(MIN_IDF)                                                                                                                                                                                   
    assert compute_idf("of") == pytest.approx(MIN_IDF)                                                                                                                                                                                  
                                        
                                    
def test_compute_idf_rare_higher_than_common():                                                                                                                                                                                           
    assert compute_idf("subterranean") > compute_idf("fox") > compute_idf("the")
                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                        
def test_compute_idf_unknown_word_is_max():        
    assert compute_idf("xyzznoword") == pytest.approx(1.0)                                                                                                                                                                                
                                            
                                                                                                                                                                                                                                        
def test_tokenize_preserves_raw_for_display():                                                                                                                                                                                          
    s = tokenize_script("The quick brown fox.")                                                                                                                                                                                           
    assert s.normalized == ["the", "quick", "brown", "fox"]
    assert s.display == ["The", "quick", "brown", "fox"]                                                                                                                                                                                  
                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                        
def test_tokenize_sentences():                         
    s = tokenize_script("Hello world. How are you? Fine!")                                                                                                                                                                                
    assert len(s.sentences) == 3                                                                                                                                                                                                        
    assert s.sentences[0] == (0, 2)
    assert s.sentences[1] == (2, 5)                                                                                                                                                                                                       
    assert s.sentences[2] == (5, 6)                    
                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                        
def test_tokenize_handles_contractions():                                                                                                                                                                                                 
    s = tokenize_script("Don't go.")                   
    assert s.normalized == ["dont", "go"]                                                                                                                                                                                                 
                                                                                                                                                                                                                                        
                                        
def test_find_sentence_for_token():                                                                                                                                                                                                       
    s = tokenize_script("Hello world. How are you?")
    assert find_sentence(0, s.sentences) == (0, 2)                                                                                                                                                                                        
    assert find_sentence(1, s.sentences) == (0, 2)                                                                                                                                                                                      
    assert find_sentence(2, s.sentences) == (2, 5)                                                                                                                                                                                        
    assert find_sentence(99, s.sentences) == (99, 99)
                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                        
def test_script_and_transcript_pipelines_match():  
    text = "Hello, world!"                             
    script = tokenize_script(text).tokens                                                                                                                                                                                                 
    transcript = tokenize_transcript(text)
    assert [t.norm for t in script] == [t.norm for t in transcript]                                                                                                                                                                       
    assert [t.metaphone for t in script] == [t.metaphone for t in transcript]                                                                                                                                                           
    assert [t.idf for t in script] == [t.idf for t in transcript]
                                                                                                                                                                                                                                        
                                
def test_tokenize_skips_pure_punctuation():                                                                                                                                                                                               
    s = tokenize_script("!!! ??? ...")                                                                                                                                                                                                  
    assert s.normalized == []                                                                                                                                                                                                             
                                                                                                                                                                                                                                        
                                                    
def test_tokenize_metaphone_populated():               
    s = tokenize_script("Quick brown fox jumps")                                                                                                                                                                                          
    assert all(t.metaphone for t in s.tokens)
                                                                                                                                                                                                                                        
                                                                                                                                                                                                                                        
def test_tokenize_empty_returns_empty():           
    s = tokenize_script("")                                                                                                                                                                                                               
    assert len(s) == 0                                                                                                                                                                                                                  
    assert s.sentences == ()
    