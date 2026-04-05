# import re

# class LexicalAnalyzer:
#     def __init__(self):
#         self.specs = [
#             ('COMMENT',    r'/\*[\s\S]*?\*/'),          # Ignore comments
#             ('KEYWORD',    r'\b(int|if|then|else|endif|while|do|enddo|print)\b'),
#             ('REL_OP',     r'<=|>=|==|!=|<|>'),         # Relational Operators
#             ('ARITH_OP',   r'[+\-*/]'),                 # Arithmetic Operators
#             ('ASSIGN',     r'='),                       # Assignment Operator
#             ('BRACKET',    r'[\[\]()]'),                # Brackets and Parentheses
#             ('PUNCT',      r'[;,]'),                    # Punctuation
#             ('NON_TERMINALS',   r'<[a-z]+>'),           # Non-Terminals 
#             ('ID',         r'[a-z][a-z0-9]*'),          # Identifiers 
#             ('CONSTANT',   r'\d+'),                     # Constants 
#             ('SKIP',       r'[ \t\n\r]+'),              # Whitespace/Tabs/Newlines
#             ('MISMATCH',   r'.'),                       # Error handling
#         ]
        
#         self.regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.specs)

#     def tokenize(self, code):
#         token_list = []
#         for match in re.finditer(self.regex, code):
#             kind = match.lastgroup
#             value = match.group()
            
#             # Requirement: Ignore redundant spaces, tabs, newlines, and comments
#             if kind == 'SKIP' or kind == 'COMMENT':
#                 continue
#             elif kind == 'MISMATCH':
#                 print(f"LEXICAL ERROR: Unexpected character '{value}'")
#                 continue
            
#             token_list.append((kind, value))
#         return token_list

# # Example Input based on your BNF
# input_code = """
# /* Scoping and Array Test */
# int a[5], i;
# i = 0;
# while i < 5 do
#     if i != 2 then
#         print(a[i]);
#     endif
#     i = i + 1;
# enddo
# """

# lexer = LexicalAnalyzer()
# tokens = lexer.tokenize(input_code)

# # Displaying the Results
# print(f"{'CATEGORY':<15} | {'TOKEN VALUE'}")
# print("-" * 30)
# for i, j in tokens:
#     print(f"{i:<15} : {j}")
    
    
    
    
import re

class LexicalAnalyzer:
    def __init__(self):
        self.specs = [
            ('SKIP',       r'[ \t\n\r]+'),             
            ('COMMENT',    r'/\*[\s\S]*?\*/'),          
            ('keyword',    r'\b(int|if|then|else|endif|while|do|enddo|print)\b'),
            ('relational_operator', r'<=|>=|==|!=|<|>'),
            ('operator',   r'[+\-*/=\[\]()]'),         
            ('punctuation', r'[;,]'),
            ('identifier', r'[a-z][a-z0-9]*'),
            ('constant',   r'\d+'),
            ('MISMATCH',   r'.'),                       
        ]
        
        # Master regular expression
        self.regex = '|'.join(f'(?P<{name}>{pattern})' for name, pattern in self.specs)

    def tokenize(self, code):
        token_list = []
        for match in re.finditer(self.regex, code):
            kind = match.lastgroup
            value = match.group()
            
            if kind == 'SKIP' or kind == 'COMMENT':
                continue
            elif kind == 'MISMATCH':
                continue
            
            token_list.append((value, kind))
        return token_list

# Test Execution 
input_code = """
/* Array Test */
int a[5], i;
i = 0;
while i < 5 do
    if i != 2 then
        print(a[i]);
    endif
    i = i + 1;
enddo
"""

    
lexer = LexicalAnalyzer()
tokens = lexer.tokenize(input_code)

# Displaying the Results
print(f"{'CATEGORY':<15} | {'TOKEN VALUE'}")
print("-" * 30)
for i, j in tokens:
    print(f"{i:<15} : {j}")