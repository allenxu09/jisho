#%% IMPORTS
from re import fullmatch as fm
from configparser import ConfigParser
from time import time

#%% GLOBAL VARIABLES
DICT_PATH = "buta014.dic"
ENCODING = "shift_JIS"
TRANS = {
    "？": "?",
    "⋆": "*",
    "＊": "*",
    "【": "[",
    "】": "]",
    "「": "[",
    "」": "]",
    "『": "[",
    "』": "]",
    "＆": "&",
    "｜": "|",
    "！": "!",
    "（": "(",
    "）": ")",
    "《": "<",
    "》": ">",
    "＜": "<",
    "＞": ">",
    "＠": "@",
    "；": ";",
    "＝": "=",
    "“": "\"",
    "”": "\"",
    "‘": "\'",
    "’": "\'",
    "｛": "{",
    "｝": "}",
    "０": "0",
    "１": "1",
    "２": "2",
    "３": "3",
    "４": "4",
    "５": "5",
    "６": "6",
    "７": "7",
    "８": "8",
    "９": "9",
    "０": "0"

}

PI = 3.1415927 # 悄悄藏一个π

KANA = set("あいうえおかがきぎくぐけげこごさざしじすずせぜそぞただちぢつづてでとどなにぬねのはばぱひびぴふぶぷへべぺほぼぽまみむめもやゆよらりるれろわをんー")

ULETTER = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
LLETTER = set("abcdefghijklmnopqrstuvwxyz")

PUNC = set("?*[-]&|!()<>@;=\"\'{}")

NUM = set("0123456789")

ALLOW = KANA | ULETTER | LLETTER | PUNC | NUM

# x for [aa], q for [nn]
L2K = {
    "x": "あいうえお",
    "k": "かきくけこ",
    "s": "さしすせそ",
    "t": "たちつてと",
    "n": "なにぬねの",
    "h": "はひふへほ",
    "m": "まみむめも",
    "y": "やゆよ",
    "r": "らりるれろ",
    "w": "わを",
    "g": "がぎぐげご",
    "z": "ざじずぜぞ",
    "d": "だぢづでど",
    "b": "ばびぶべぼ",
    "p": "ぱぴぷぺぽ",
    "a": "あかさたなはまやらわがざだばぱ",
    "i": "いきしちにひみりぎじぢびぴ",
    "u": "うくすつぬふむゆるぐずづぶぷ",
    "e": "えけせてねへめよれげぜでべぺ",
    "o": "おこそとのほもよろをごぞどぼぽ",
    "q": "ん"
}

TIME_LIMIT = 20 # 20s

for i in ALLOW:
    TRANS[i] = i

# Read File
with open(DICT_PATH, 'r', encoding=ENCODING) as f:
    file = f.readlines()
dict = [i.strip() for i in file]

# Hash Table
hasht = {}
for i in dict:
    hasht[hash(i)] = i

# Create indices for faster lookup
dict_by_length = {}
dict_by_first_char = {}
for word in dict:
    # Index by length
    length = len(word)
    if length not in dict_by_length:
        dict_by_length[length] = []
    dict_by_length[length].append(word)
    
    # Index by first character
    if word:
        first_char = word[0]
        if first_char not in dict_by_first_char:
            dict_by_first_char[first_char] = []
        dict_by_first_char[first_char].append(word)

# i18n
config = ConfigParser()
config.read("./i18n.cfg",encoding="utf-8")

#%% END

class JishoSearcher():
    #%% Initialization & Other Functions
    def  __init__(self, lang: str = "en"):
        # Language Setup
        self.lang = lang
        # Cache for compiled patterns and results
        self._pattern_cache = {}
        self._result_cache = {}


    # Raise an error message
    def _error(self, text:str, ex:str="") -> str: # ex: explain
        res = "#" + config[self.lang][text]
        res += ":" + ex

        return res
    
    # Normalization before processing
    def _normalize(self, expr:str) -> str:
        inbracketround = 0
        inbracketsquare = 0
        inbracketangle = 0
        inbracketcurly = 0
        inbracket = True # square, angle, curly
        normalized = [' ']

        for c in expr:
            inbracket = bool(inbracketsquare + inbracketangle + inbracketcurly)
            if c == ' ' or c == '\n':
                continue
            
            try:
                c = TRANS[c] # Translate
            except KeyError:
                # Some character is not allowed
                return self._error("normalizerange",ex=c)

            ### START BRACKET
            if c == '[':
                if inbracket:
                    return self._error("bracket")
                inbracketsquare += 1
                if normalized[-1] != '*' and normalized[-1] != '?' and normalized[-1] != '}':
                    return self._error("syntax", ex=normalized[-1])
                normalized.append(c)
                
            elif c == ']':
                if not bool(inbracketsquare):
                    return self._error("bracket")
                inbracketsquare -= 1
                normalized.append(c)

            elif c == '(':
                if bool(inbracketangle) or bool(inbracketcurly):
                    return self._error("bracket")
                inbracketround += 1
                normalized.append(c)
            elif c == ')':
                if not bool(inbracketround):
                    return self._error("bracket")
                inbracketround -= 1
                normalized.append(c)

            elif c == '<':
                if inbracket:
                    return self._error("bracket")
                inbracketangle += 1
                normalized.append(c)
            elif c == '>':
                if not bool(inbracketangle):
                    return self._error("bracket")
                inbracketangle -= 1
                normalized.append(c)

            elif c == '{':
                if inbracket:
                    return self._error("bracket")
                inbracketcurly += 1
                if normalized[-1] != '*' and normalized[-1] != ']':
                    return self._error("syntax",ex=normalized[-1])
                normalized.append(c)

            elif c == '}':
                if not bool(inbracketcurly):
                    return self._error("bracket")
                inbracketcurly -= 1
                normalized.append(c)

            ### END BRACKET

            elif c.isalpha(): # kana + letters
                if inbracketcurly:
                    if c == 'ー':
                        normalized.append('-')
                    else:
                        return self._error("syntax", ex=c)
                elif inbracketsquare:
                    normalized.append(c.lower())
                else:
                    normalized.append(c.upper())

            elif c in NUM:
                if inbracketsquare or inbracketangle:
                    return self._error("syntax")
                
                normalized.append(c)

            else: # other characters
                normalized.append(c)

            
        expr = "".join(normalized[1:])
        # Remove brackets with no text in it
        expr = expr.replace("()", "").replace("{}","")
        expr = expr.replace("<>", "").replace("[]", "")

        if inbracketround or inbracketsquare or inbracketangle or inbracketcurly:
            return self._error("bracket")
        
        return expr
        
    # Whether the expression is in the dictionary
    def _indict(self, expr: str) -> bool:
        return expr in hasht
    
    # Permutation of the expression (for <...>)
    def _permutation(self, expr: str):
        if len(expr) == 1:
            return [expr]
        res = []
        for i in range(len(expr)):
            tmp = self._permutation(expr[:i] + expr[i+1:])
            for j in tmp:
                res.append(expr[i] + j)

        res = list(set(res)) # unique
        return res
    
    #%% Set Operations
    def _union(self, a:str, b:str) -> str:
        return ''.join(set(a) | set(b))
    
    def _intersection(self, a:str, b:str) -> str:
        return ''.join(set(a) & set(b))
    
    def _complement(self, a:str) -> str:
        return ''.join(set(KANA) - set(a))

    
    #%% Splitter
    def _splitter_re(self, expr, format):
        length = format[0]
        if len(format) == 1:
            if length > 0 and len(expr) != length: # length not match
                return
            elif length < 0 and len(expr) < -length:
                return
            else: # length match, recording the answer
                self._splitter_ans.append(self._splitter_stack + [expr,])
                return
        else:
            if length > 0:
                if len(expr) < length:
                    return
                else:
                    self._splitter_stack.append(expr[:length])
                    self._splitter_re(expr[length:], format[1:])
                    self._splitter_stack.pop()
                    return
            else:
                # why -length
                # -> consider the minimum length
                for i in range(-length, len(expr)+1):
                    self._splitter_stack.append(expr[:i])
                    self._splitter_re(expr[i:], format[1:])
                    self._splitter_stack.pop()

    # split the expr according to the format, the length limit is set by format
    def _splitter(self, expr, format): 
        # 2 means length = 2
        # -2 means length >= 2
        self._splitter_stack = []
        self._splitter_ans = []
        self._splitter_re(expr, format)
        return self._splitter_ans
    

    
    #%% Handle the brackets
    def _curly(self, expr:str) -> str:
        if expr == "":
            return ""
        else:
            expr = expr.replace('-',',')
            for i in expr.split(','):
                if i == "":
                    continue
                if not i.isdigit() or int(i) < 0 or int(i) > 10:
                    return self._error("syntax", ex=expr)
            return "{" + expr + "}"
        
    
    def _square(self, expr:str):
        if expr == "":
            return ""
        if expr[0] == '(' and expr[-1] == ')':
            level = 1
            for i in range(1, len(expr)-1):
                if expr[i] == '(':
                    level += 1
                elif expr[i] == ')':
                    level -= 1
                if level == 0:
                    break
            if level != 0:
                expr = expr[1:-1]

        # Find &|
        inbracket = 0
        opt = -1
        for i in range(len(expr)):
            if opt == "(":
                inbracket += 1
            elif expr[i] == ")":
                inbracket -= 1
            if inbracket == 0 and (opt == -1 and (expr[i] == '&' or expr[i] == '|')):
                opt = i
                break
            
        if opt != -1: # Found
            left = self._square(expr[:opt])
            right = self._square(expr[opt+1:])
            if left[0] == "#" or right[0] == "#":
                return left if left[0] == "#" else right
            return self._intersection(left, right) if expr[opt] == '&' else self._union(left, right)

        elif expr[0] == '!': #not
            text = self._square(expr[1:])
            if text[0] == "#": # Error
                return text
            else:
                return self._complement(text)

        else: # normal
            expr = expr.replace("aa", 'x').replace("nn",'q')
            res = ""
            try:
                for i in expr:
                    if i in KANA:
                        res = self._union(res, i)
                    else:
                        res = self._union(res, L2K[i])
            except:
                return self._error("syntax", ex=expr)
            
            return res

    # Process the brackets
    # _square + _curly
    def _bracket(self, expr:str):

        # one bracket only
        if expr.count('[') > 1 or expr.count('{') > 1:
            return self._error("syntax", ex=expr)
        
        res = ""
        if expr.count('[') == 1:
            res += '['
            res += self._square(expr[expr.find('[')+1:expr.find(']')])
            res += ']'
        if expr.count('{') == 1:
            res += self._curly(expr[expr.find('{')+1:expr.find('}')])
        
        return res



    #%% Process Expression _process_normal and _process_qat

    # Expression -> regex
    # Process ?* and brackets
    def _regex(self, expr:str) -> str:
        res = ""
        i = 0
        while i < len(expr):
            if expr[i] == '?' or expr[i] == "*":

                ### READ BRACKET
                j = i + 1
                
                while True:
                    if j == len(expr):
                        break
                    iscurly = False
                    if expr[j] == '{':
                        iscurly = True
                    elif expr[j] == '[':
                        iscurly = False
                    else:
                        break

                    while (iscurly and expr[j] != '}') or (not iscurly and expr[j] != ']'):
                        j += 1
                        if j == len(expr):
                            break
                    j += 1
                ###

                if j == i + 1: # No Bracket
                    if expr[i] == '?':
                        res += '.'
                    else:
                        res += '.*'

                else: # Handle Bracket
                    bracket = self._bracket(expr[i+1:j])
                    if bracket[0] == "#": # Error
                        return bracket
                    
                    if expr[i] == '?':
                        if '{' in bracket:
                            return self._error("syntax", ex=expr[i:j])
                        elif '[' in bracket:
                            res += bracket
                        else:
                            return self._error("syntax", ex=expr[i:j])
                    elif expr[i] == '*': # expr[i] == "*"
                        if '[' in bracket:
                            if '{' in bracket:
                                res += bracket
                            else:
                                res += bracket + '*'
                        else:
                            if '{' in bracket:
                                res += '.' + bracket
                i = j

            else:
                res += expr[i]
                i += 1

        return res
    
    # Process @ and QAT letters
    # and pass it to _regex
    def _atQAT(self, expr:str) -> str: # TODO
        if "@" in expr or (any([c.isalpha() and c.isupper() for c in expr])): # has @ or QAT letters
            # break down & format
            exprs = []
            counter = 0
            format = []
            while counter < len(expr):
                letter = expr[counter]

                if letter == "@": # @
                    exprs.append(letter)
                    format.append(-2)

                    counter += 1

                elif letter in ULETTER: # QAT letter
                    exprs.append(letter)
                    format.append(self.qat_letters[ord(letter)-65])

                    counter += 1

                else: # Normal expression: _regex
                    begin = counter
                    while counter < len(expr) and expr[counter] != "@" and (expr[counter] not in ULETTER):
                        counter += 1

                    exprs.append(self._regex(expr[begin:counter]))
                    format.append(0)

            return ["@", exprs, format]
        
        else: # no @ or QAT letters
            return self._regex(expr)

    # Turn the expression into regex tree
    # Permutate <...>
    # and pass it to _atQAT
    # lg: less than, greater than
    def _lg(self, expr:str) -> str:
        if "<" in expr:

            # Permutate <>
            words = []
            i = 0
            while i < len(expr):
                if expr[i] == '<': # rearrange
                    j = i+1
                    while j < len(expr) and expr[j] != '>':
                        j += 1
                    words.append(self._permutation(expr[i+1:j].replace('?','.').replace("*",".*"))) # TODO
                    i = j + 1
                else: # normal
                    j = i+1
                    while j < len(expr) and expr[j] != '<':
                        j += 1
                    words.append(expr[i:j])
                    i = j

            # Combine words -> res
            res = []
            pointer = 0

            if type(words[0]) == list: # first <>
                res.append("")

            while pointer < len(words):
                if type(words[pointer]) == list: # <>
                    res2 = []
                    for i in res:
                        for j in words[pointer]:
                            res2.append(i+j)
                    res = res2

                elif type(words[pointer]) == str: # normal
                    res2 = []
                    for i in res:
                        res2.append(i+words[pointer])
                    res = res2
                pointer += 1
            
            # _atQAT
            res = [self._atQAT(i) for i in res]

            for i in res:
                if i[0] == "#": # Error
                    return i
                
            return ['|', res]
        else:
            return self._atQAT(expr)

    # Process global &|! (gb: global boolean)
    # and pass it to _lg
    def _gb(self, expr:str):
        #print(expr)
        if expr == "": # expr shouldn't be empty
            return self._error("empty")
        
        # Remove the parenthesis
        while expr[0] == '(' and expr[-1] == ')':
            level = 1
            for i in range(1, len(expr)-1):
                if expr[i] == '(':
                    level += 1
                elif expr[i] == ')':
                    level -= 1
                if level == 0:
                    break
            if level != 0:
                expr = expr[1:-1]
        #print(expr)
        # find global &|
        inbracketsquare = 0
        inbracketround = 0
        ands = []
        ors = []
        for i in range(len(expr)):
            if expr[i] == '[':
                inbracketsquare += 1
            elif expr[i] == ']':
                inbracketsquare -= 1
            elif expr[i] == '(':
                inbracketround += 1
            elif expr[i] == ')':
                inbracketround -= 1
            if not bool(inbracketsquare) and not bool(inbracketround):
                if expr[i] == '&':
                    ands.append(i)
                elif expr[i] == '|':
                    ors.append(i)

        #print(ands,ors)

        # OR
        if len(ors) > 0:
            exprs = []
            last = 0
            for i in ors:
                text = self._gb(expr[last:i])
                if text[0] == "#": # Error
                    return text
                exprs.append(text)
                last = i+1
            exprs.append(self._gb(expr[last:]))
            return ['|', exprs]
        
        # AND
        elif len(ands) > 0:
            exprs = []
            last = 0
            for i in ands:
                text = self._gb(expr[last:i])
                if text[0] == "#": # Error
                    return text
                exprs.append(text)
                last = i+1
            exprs.append(self._gb(expr[last:]))
            return ['&', exprs]
        
        # NOT
        elif expr[0] == "!":
            return ["!", [self._gb(expr[1:]), ]]
        
        # normal case, pass it to _lg
        else:
            return self._lg(expr)

    # Process Normal Expression (_gb)
    def _process_normal(self, expr:str):
        return self._gb(expr)

    # Process QAT Expression (_atQAT)
    def _process_qat(self, expr:str):
        return self._atQAT(expr)
    
    #%% Match: Normal

    # normal full match
    def _nfm(self, expr, word):
        if type(expr) == str:
            if expr == "@": # @
                return self._indict(word)
                
            else: # normal cases
                return fm(expr, word) != None
        else:
            opt = expr[0]
            exprs = expr[1] # a list of expressions
            if opt == '&':
                for i in exprs:
                    if self._nfm(i, word) == False:
                        return False
                return True
            elif opt == '|':
                for i in exprs:
                    if self._nfm(i, word) == True:
                        return True
                return False
            elif opt == '!':
                return not self._nfm(exprs[0], word)
            elif opt == "@":
                # Split the word according to the format
                format = expr[2]
                split = self._splitter(word, format)
                if split == []:
                    return False
                
                # Try all the cases
                for case in split:
                    flag = True
                    for j in range(len(case)):
                        temp = self._nfm(exprs[j], case[j])
                        flag &= temp

                    if flag:
                        return True
                    
                return False

    #%% Match: QAT QAQ

    # Set up QAT QAQ
    def _setup_qat(self):
        self.qat_exprs = [] # Expressions (["@",,] or "")
        self.qat_letters = [0 for i in range(26)] # length limit

        self.qat_current_letters = ['' for i in range(26)] # current letters
        self.qat_current_answer = [] # current answer

        self.qat_num_limit = 0
        self.qat_start_time = time()

        self.qat_answers = []
        self.qat_error = " "
        self.stop = False

    # QAT (dfs)
    def _qat(self, depth:int):
        # if time() - self.qat_start_time > TIME_LIMIT: # timeout
        #     self.qat_error = self._error("timeout")
        #     self.stop = True
        #     return
        if self.stop: # Stop
            return
        if depth == len(self.qat_exprs): # reach the end
            self.qat_answers.append(";".join(self.qat_current_answer))
            if len(self.qat_answers) >= self.qat_num_limit:
                self.stop = True
            return
        else:
            exprssion = self.qat_exprs[depth]
            if type(exprssion) == str: # normal expression
                # Use optimized search candidates for QAT as well
                search_candidates = dict
                if hasattr(exprssion, '__len__') and isinstance(exprssion, str) and '.*' not in exprssion and '.' not in exprssion:
                    target_length = len(exprssion)
                    if target_length in dict_by_length:
                        search_candidates = dict_by_length[target_length]
                
                for word in search_candidates: # iterate the dictionary
                    if self._nfm(exprssion, word) == True:
                        self.qat_current_answer[depth] = word
                        self._qat(depth + 1)
                    if self.stop:
                        return

            else: # has @ or QAT letters

                # Substitute defined QAT letters
                # Find undefined letters
                expr, format = exprssion[1][:], exprssion[2][:]  # Shallow copy instead of deep copy
                undefined = []
                for i in range(len(expr)): # Substitute
                    if expr[i] in ULETTER: # QAT letter
                        if self.qat_current_letters[ord(expr[i])-65] != "": # Defined
                            expr[i] = self.qat_current_letters[ord(expr[i])-65]
                            format[i] = len(expr[i])
                        else: # Not defined
                            undefined.append(i)

                for word in dict:
                    split = self._splitter(word, format)
                    if split == []:
                        continue

                    self.qat_current_answer[depth] = word

                    for case in split:
                        # Build new expr
                        valid = True
                        expr_new = expr[:]  # Shallow copy
                        defined = []
                        defined_val = []
                        for i in range(len(expr)):
                            if expr[i] in ULETTER or expr[i] == "@":
                                if expr_new[i] in defined:
                                    if defined_val[defined.index(expr_new[i])] != case[i]:
                                        valid = False
                                        break
                                    else:
                                        expr_new[i] = case[i]

                                elif i in undefined:
                                    defined.append(expr_new[i])
                                    defined_val.append(case[i])
                                    expr_new[i] = case[i]

                                elif expr_new[i] != case[i]:
                                    expr_new[i] = case[i]

                        if not valid:
                            continue

                        if self._nfm("".join(expr_new), word) == True: # Match
                            # Update current letters
                            for i in undefined:
                                self.qat_current_letters[ord(expr[i])-65] = case[i]

                            self._qat(depth + 1)

                            # Rollback current letters
                            for i in undefined:
                                self.qat_current_letters[ord(expr[i])-65] = ""
                        
                    if self.stop:
                        return
                    

    #%% Search (Main Processing)

    # Search
    def search(self, expr: str, num: int = 200) -> str:
        # Check cache first
        cache_key = (expr, num)
        if cache_key in self._result_cache:
            return self._result_cache[cache_key]
            
        self._setup_qat()
        # Empty
        if expr == "":
            return self._error("empty")
        
        expr = self._normalize(expr)
        if expr[0] == '#': # ERR
            return expr

        # Process
        # - Normal
        if ';' not in expr:
            expr_re = self._process_normal(expr)
            if expr_re[0] == "#": # Error
                return expr_re
            
            res = []
            res_len = 0
            start_time = time()
            
            # Use optimized search based on pattern characteristics
            search_candidates = dict  # Default: search all
            
            # If we can determine a fixed length, use length index
            if hasattr(expr_re, '__len__') and isinstance(expr_re, str) and '.*' not in expr_re and '.' not in expr_re:
                # Simple string match - exact length
                target_length = len(expr_re)
                if target_length in dict_by_length:
                    search_candidates = dict_by_length[target_length]
            
            for i in search_candidates: # Search
                if self._nfm(expr_re, i) == True: # Match
                    res_len += 1
                    res.append(i)
                    if res_len == num:
                        break

                if time() - start_time > TIME_LIMIT: # timeout
                    return self._error("timeout")

            # Cache the result
            self._result_cache[cache_key] = res
            return res
        
        # - QAT QAQ
        else:
            # Reject <>
            if "<" in expr or ">" in expr:
                return self._error("syntax", ex="< or > in QAT")
            
            self.qat_num_limit = num

            exprs = expr.split(";")

            self.qat_letters = [0 for i in range(26)]

            for i in range(len(exprs)-1, -1, -1):
                if exprs[i] == "": # Delete Empty Expressions
                    del exprs[i]
                else:
                    while exprs[i][0] == '(' and exprs[i][-1] == ')': # Remove unnecessary ()
                        exprs[i] = exprs[i][1:-1]
                    # Register Existed Letters
                    # 0 : not exist, -1 : exist
                    for j in range(26):
                        if chr(j+65) in exprs[i]:
                            self.qat_letters[j] = -1

            if exprs == []: # check if empty
                return self._error("empty")

            # Find Length Limitation
            for i in range(len(exprs)-1, -1, -1):
                if '=' in exprs[i]: # Fixed Length
                    condition = exprs[i].split('=')
                    # Check format
                    if len(condition) != 2 or \
                        not condition[1].isnumeric() or \
                        len(condition[0]) != 3 or \
                        condition[0][0] != '|'or \
                        condition[0][2] != '|':
                        return self._error("syntax", ex=exprs[i])
                    
                    # Check value
                    if not (0 <= ord(condition[0][1])-ord('A') < 26) or \
                        not (0 < int(condition[1]) < 10):
                        return self._error("syntax", ex=exprs[i])

                    if self.qat_letters[ord(condition[0][1])-ord('A')] != -1: # defined
                        return self._error("syntax", ex=exprs[i])

                    self.qat_letters[ord(condition[0][1])-ord('A')] = int(condition[1])

                    del exprs[i] # Delete the expression
            
            if exprs == []: # check if empty
                return self._error("empty")
            
            # reject global &|!
            for i in range(len(exprs)):
                inbracket_square = 0
                inbracket_round = 0
                for j in range(len(exprs[i])):
                    if exprs[i][j] == '[':
                        inbracket_square += 1
                    elif exprs[i][j] == ']':
                        inbracket_square -= 1
                    elif exprs[i][j] == '(':
                        inbracket_round += 1
                    elif exprs[i][j] == ')':
                        inbracket_round -= 1
                    if not bool(inbracket_square) and not bool(inbracket_round):
                        if exprs[i][j] in ['&', '|', '!']:
                            return self._error("syntax", ex=exprs[i])
            
            # Sort, put the most number of letters first
            exprs.sort(key = lambda x: sum([(c.isalpha() and c.isupper()) for c in x]), reverse=True)

            letter_num = sum([(i != 0) for i in self.qat_letters]) # number of letters

            # if letter_num != 0: # QAT (dfs)

            self.qat_exprs = [self._process_qat(i) for i in exprs]
            self.qat_current_answer = ['' for i in exprs]
            for i in self.qat_exprs:
                if i[0] == "#": # Error
                    return i

            self._qat(0)

            if self.qat_error[0] == "#": # Error
                return self.qat_error
            else:
                # Cache QAT results
                self._result_cache[cache_key] = self.qat_answers
                return self.qat_answers
    
    # print the result  
    def search_print(self, expr: str, num: int = 200, file=False) -> None:
        start_time = time()
        try:
            res = self.search(expr, num=num)
        except Exception as e:
            print(f"Unexpected Error: {str(e)}")
            return
        
        elapsed = time() - start_time
        print(f"Expr:{expr}")
        print(f"Found {len(res)} items in {elapsed:.2f} seconds:")
        print()

        if not res:
            print("No Solution.")
        elif isinstance(res, list) and res and res[0].startswith("#"):  # Error
            print(res[0])
        else:
            # More efficient output formatting
            for i, item in enumerate(res):
                print(item, end="")
                if (i + 1) % 10 == 0:
                    print()  # newline every 10 items
                else:
                    print("\t", end="")
        
        print("\n")
    #%% END

#%% Main Programme

def main():
    test = JishoSearcher(lang="zh")
    # expr = "abcd"
    # format = [0,-2, 0, 0]
    # for i in test._splitter(expr, format):
    #     print(i)
    # print(len(test._splitter(expr, format)))
    # flag = True
    # for i in dict:
    #     flag = test._indict(i) and flag
    # print(test._indict("awa"))
    #test.search_print("AB;!JI;QW")
    # test.search_print("！＊｛５ー｝＆＜あ＞＊｛１ー３｝「！o」い")
    # print(test._process_normal("Aああ@あ*{1-3}ああO"))
    # test.search_print("う＠う")
    # test.search_print("CA;C;A?[o];ACB;(((AB?[C])));|A|=2;|B|=2;|C|=2")
    test.search_print("AB?ま;A;B",num=20)

if __name__ == "__main__":
    main()