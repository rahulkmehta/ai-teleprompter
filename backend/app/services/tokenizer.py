"""Tokenization that feeds alignment module
Both the script and live transcripts from Deepgram pass through this module so their token surfaces match exactly when the aligner compares them.
Each Token carries the raw form (for display), normalized form (for matching), phonetic Metaphone code (for catching mispronunciations), and IDF weight (so common words don't dominate alignment).
"""

import re
import jellyfish
from dataclasses import dataclass
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
    if not text:                                       
        return ""                                                                                                                                                                                                                         
    try:                              
        return jellyfish.metaphone(text)                                                                                                                                                                                                  
    except Exception:                                                                                                                                                                                                                   
        return ""                           
                                        
                                
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
                                    
    chunks = SENTENCE_END_REGEX.split(text.strip())                                                                                                                                                                                              
    for chunk in chunks:                                                                                                                                                                                                                
        if not chunk.strip():               
            continue                    
        start = len(tokens)     
        for match in WORD_REGEX.finditer(chunk):                                                                                                                                                                                             
            tok = _build_token(match.group(0))         
            if tok is not None:                                                                                                                                                                                                           
                tokens.append(tok)                                                                                                                                                                                                      
        end = len(tokens)                                                                                                                                                                                                                 
        if end > start:         
            sentences.append((start, end))                                                                                                                                                                                                                                                                                                                                                                                                                     
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
    