import re

# token types using regular expressions
TOKEN_SPECIFICATION = [
    ('KEYWORD',    r'\b(int|if|else|while|return)\b'), # Keywords
    ('IDENTIFIER', r'[a-zA-Z_][a-zA-Z0-9_]*'),         # Identifiers
    ('LITERAL',     r'\d+'),                           # Literals
    ('OPERATOR',   r'[+\-*/]'),                         # Operators
    ('DELIMITER',  r'[;{}]'),                           # Delimiters
    ('WHITESPACE', r'\s+'),                             # Skip spaces
    ('MISMATCH',   r'.'),                               # Any other character
]

def tokenize(code):
    # Join all patterns into one master regex with named groups
    tok_regex = '|'.join('(?P<%s>%s)' % pair for pair in TOKEN_SPECIFICATION)
    
    tokens = []
    
    # Iterate over all matches in the source code
    for mo in re.finditer(tok_regex, code):
        kind = mo.lastgroup
        value = mo.group()
        
        if kind == 'WHITESPACE':
            continue
        elif kind == 'MISMATCH':
            print(f"Error: Unexpected character '{value}'")
            continue
            
        tokens.append((kind, value))
        
    return tokens

# --- Main Implementation ---
if __name__ == "__main__":
    # Sample C++ code snippet to test the lexer
    cpp_code = """
    int x = 10;
    if (x > 5) {
        return x + 2;
    } else {
        while (x - 1) {
            return 0;
        }
    }
    """

    print("--- Lexical Analysis Results ---")
    print(f"{'Token Type':<15} | {'Value'}")
    print("-" * 30)
    
    results = tokenize(cpp_code)
    
    for token_type, value in results:
        print(f"{token_type:<15} | {value}")