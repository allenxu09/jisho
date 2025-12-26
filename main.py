from constants import *

class JishoSearcher():
    #%% Initialization & Other Functions
    def  __init__(self, lang: str = "en"):
        # Language Setup
        self.lang = lang

    # Raise an error message
    def _error(self, text:str, ex:str="") -> str: # ex: explain
        res = "#" + config[self.lang][text]
        res += ":" + ex

        return res
    
    # Normalization before processing - optimized version
    def _normalize(self, expr: str) -> str:
        if not expr:
            return self._error("empty")
            
        bracket_counts = [0, 0, 0, 0]  # round, square, angle, curly
        normalized = []

        for c in expr:
            if c in ' \n':
                continue
            
            # Translate using dictionary lookup
            c = TRANS.get(c, c)
            if c not in ALLOW:
                return self._error("normalizerange", ex=c)

            # Handle brackets with simplified logic
            if c == '[':
                if any(bracket_counts[1:]):  # any square, angle, or curly open
                    return self._error("bracket")
                bracket_counts[1] += 1
                if normalized and normalized[-1] not in '*?}':
                    return self._error("syntax", ex=normalized[-1])
                normalized.append(c)
                
            elif c == ']':
                if bracket_counts[1] <= 0:
                    return self._error("bracket")
                bracket_counts[1] -= 1
                normalized.append(c)

            elif c == '(':
                if bracket_counts[2] or bracket_counts[3]:  # angle or curly open
                    return self._error("bracket")
                bracket_counts[0] += 1
                normalized.append(c)
                
            elif c == ')':
                if bracket_counts[0] <= 0:
                    return self._error("bracket")
                bracket_counts[0] -= 1
                normalized.append(c)

            elif c == '<':
                if any(bracket_counts[1:]):  # any square, angle, or curly open
                    return self._error("bracket")
                bracket_counts[2] += 1
                normalized.append(c)
                
            elif c == '>':
                if bracket_counts[2] <= 0:
                    return self._error("bracket")
                bracket_counts[2] -= 1
                normalized.append(c)

            elif c == '{':
                if any(bracket_counts[1:]):  # any square, angle, or curly open
                    return self._error("bracket")
                bracket_counts[3] += 1
                if normalized and normalized[-1] not in '*]':
                    return self._error("syntax", ex=normalized[-1])
                normalized.append(c)
                
            elif c == '}':
                if bracket_counts[3] <= 0:
                    return self._error("bracket")
                bracket_counts[3] -= 1
                normalized.append(c)

            elif c.isalpha():  # kana + letters
                if bracket_counts[3]:  # in curly brackets
                    if c == 'ー':
                        normalized.append('-')
                    else:
                        return self._error("syntax", ex=c)
                elif bracket_counts[1]:  # in square brackets
                    normalized.append(c.lower())
                else:
                    normalized.append(c.upper())

            elif c in NUM:
                if bracket_counts[1] or bracket_counts[2]:  # in square or angle brackets
                    return self._error("syntax")
                normalized.append(c)

            else:  # other characters
                normalized.append(c)

        # Check for unclosed brackets
        if any(bracket_counts):
            return self._error("bracket")
            
        expr = "".join(normalized)
        # Remove empty brackets
        return expr.replace("()", "").replace("{}", "").replace("<>", "").replace("[]", "")
        
    # Whether the expression is in the dictionary
    def _indict(self, expr: str) -> bool:
        return hash(expr) in hasht
    
    # Permutation of the expression (for <...>) - optimized version
    def _permutation(self, expr: str):
        if len(expr) <= 1:
            return [expr]
        
        # Use itertools for better performance on larger strings
        from itertools import permutations
        return list(set(''.join(p) for p in permutations(expr)))
    
    #%% Set Operations - optimized versions
    def _union(self, a: str, b: str) -> str:
        return ''.join(set(a) | set(b))
    
    def _intersection(self, a: str, b: str) -> str:
        return ''.join(set(a) & set(b))
    
    def _complement(self, a: str) -> str:
        return ''.join(KANA - set(a))

    
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
    def _curly(self, expr: str) -> str:
        if not expr:
            return ""
        
        expr = expr.replace('-', ',')
        for part in expr.split(','):
            if part and (not part.isdigit() or not (0 <= int(part) <= 10)):
                return self._error("syntax", ex=expr)
        return "{" + expr + "}"
        
    
    def _square(self, expr: str):
        if not expr:
            return ""
            
        # Remove unnecessary outer parentheses
        while expr.startswith('(') and expr.endswith(')'):
            level = 1
            is_complete = True
            for i in range(1, len(expr)-1):
                if expr[i] == '(':
                    level += 1
                elif expr[i] == ')':
                    level -= 1
                if level == 0:
                    is_complete = False
                    break
            if is_complete:
                expr = expr[1:-1]
            else:
                break

        # Find &| operators
        inbracket = 0
        for i, char in enumerate(expr):
            if char == '(':
                inbracket += 1
            elif char == ')':
                inbracket -= 1
            elif inbracket == 0 and char in '&|':
                left = self._square(expr[:i])
                right = self._square(expr[i+1:])
                if left.startswith("#") or right.startswith("#"):
                    return left if left.startswith("#") else right
                return self._intersection(left, right) if char == '&' else self._union(left, right)

        # Handle negation
        if expr.startswith('!'):
            text = self._square(expr[1:])
            return self._complement(text) if not text.startswith("#") else text

        # Normal case - process characters
        expr = expr.replace("aa", 'x').replace("nn", 'q')
        res = ""
        try:
            for char in expr:
                addition = char if char in KANA else L2K[char]
                res = self._union(res, addition)
        except KeyError:
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
    
    # Process @, QAT letters and functions
    # and pass it to _regex
    def _atQATf(self, expr:str) -> str: # TODO
        if "@" in expr or "%" in expr or (any([c.isalpha() and c.isupper() for c in expr])): # has @ or QAT letters
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
                    format.append(self.qat_letters[ord(letter)-65])

                    if counter + 1 != len(expr) and expr[counter + 1] in ['\"', '\'']: # Voiced and semi-voiced
                        exprs.append(letter + expr[counter + 1])
                        counter += 1
                        
                    else: # Normal QAT letter
                        exprs.append(letter)

                    counter += 1
                
                elif letter == '%': # Function
                    begin = counter
                    counter += 1
                    while counter < len(expr) and expr[counter] != "%":
                        counter += 1
                    if counter == len(expr): # No ending %
                        return self._error("syntax", ex=expr[begin:])
                    
                    func = expr[begin+1:counter]
                    dprint(func)
                    
                    counter += 1
                    if expr[counter] != '(': # No opening (
                        return self._error("syntax", ex=expr[begin:])
                    counter += 1
                    while counter < len(expr) and expr[counter] == ")":
                        counter += 1
                    if counter == len(expr): # No closing )
                        return self._error("syntax", ex=expr[begin:])
                    para = expr[begin+len(func)+2:counter-1]
                    dprint(para)
                    
                    if para in ULETTER:
                        if len(para) != 1:
                            return self._error("syntax", ex=expr[begin:])
                        format.append(self.qat_letters[ord(para)-65])
                        exprs.append(para + "_" + func)
                    else:
                        funced = self._func
                    #######
                    
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
    # and pass it to _atQATf
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
            res = [""]
            pointer = 0

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
            
            # _atQATf
            res = [self._atQATf(i) for i in res]

            for i in res:
                if i[0] == "#": # Error
                    return i
                
            return ['|', res]
        else:
            return self._atQATf(expr)

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

    # Process QAT Expression (_atQATf)
    def _process_qat(self, expr:str):
        return self._atQATf(expr)
    
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
    
    # FUNCTIONS
    def _func(self, func:int, letter:str) -> str: # do a function
        ans = ""
        for i in letter:
            ans += self.func[func][2][self.func[func][1].find(i)]
            if ans[-1] == '#': # NOT FOUND
                return '#'
            
        return ans

    def _unfunc(self, func:int, letter:str) -> str: # undo a function
        ans = ""
        for i in letter:
            ans += self.func[func][1][self.func[func][2].find(i)]
            if ans[-1] == '#': # NOT FOUND
                return '#'
            
        return ans
    
    # VOICED AND UN-SEMI-VOICED
    def _voice(self, letter:str) -> str: # voice a kana
        ans = ""
        for i in letter:
            ans += VOICED_KANA[UN_VOICED_KANA.find(i)]
            if ans[-1] == '#': # NOT FOUND
                return '#'
            
        return ans

    def _semi_voice(self, letter:str) -> str: # semi-voice a kana
        ans = ""
        for i in letter:
            ans += SEMI_VOICED_KANA[UN_SEMI_VOICED_KANA.find(i)]
            if ans[-1] == '#': # NOT FOUND
                return '#'
            
        return ans

    def _un_voice(self, letter:str) -> str: # un-voice a kana
        ans = ""
        for i in letter:
            ans += UN_VOICED_KANA[VOICED_KANA.find(i)]
            if ans[-1] == '#': # NOT FOUND
                return '#'
            
        return ans

    def _un_semi_voice(self, letter:str) -> str: # un-semi-voice a kana
        ans = ""
        for i in letter:
            ans += UN_SEMI_VOICED_KANA[SEMI_VOICED_KANA.find(i)]
            if ans[-1] == '#': # NOT FOUND
                return '#'
            
        return ans

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
        
        self.qat_progress = [] # Progress of QAT
        

    # QAT (dfs)
    def _qat(self, depth:int):
        # if time() - self.qat_start_time > TIME_LIMIT: # timeout
        #     self.qat_error = self._error("timeout")
        #     self.stop = True
        #     return
        if self.stop: # Stop
            return
        if depth == len(self.qat_exprs): # reach the end
            answer_sorted = sorted(self.qat_current_answer, key = lambda x:x[1])
            answer_sorted = [x[0] for x in answer_sorted]
            self.qat_answers.append(";".join(answer_sorted))
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
                
                if DEBUG and depth == 0: # show progress if debug
                    iterate = tqdm.trange(len(search_candidates))
                else:
                    iterate = range(len(search_candidates))
                    
                for i in iterate: # iterate the dictionary
                    if self._nfm(exprssion, search_candidates[i]) == True:
                        self.qat_current_answer[depth][0] = search_candidates[i]
                        self._qat(depth + 1)
                    if self.stop:
                        return

            else: # has @ or QAT letters

                # Substitute defined QAT letters
                # Find undefined letters
                expr, format = exprssion[1][:], exprssion[2][:]  # Shallow copy instead of deep copy
                undefined = []
                for i in range(len(expr)): # Substitute
                    if expr[i][0] in ULETTER: # QAT letter
                        if self.qat_current_letters[ord(expr[i][0])-65] != "": # Defined
                            
                            if len(expr[i]) == 2: # have voice or semi-voice
                                if expr[i][-1] == '"': # voice
                                    expr[i] = self._voice(self.qat_current_letters[ord(expr[i][0])-65])
                                    if expr[i] == "#": # ERROR 
                                        return
                                    
                                elif expr[i][-1] == '\'': # semi-voice
                                    expr[i] = self._semi_voice(self.qat_current_letters[ord(expr[i][0])-65])
                                    if expr[i] == "#": # ERROR
                                        return
                                    
                            else: # not voice or semi-voice
                                expr[i] = self.qat_current_letters[ord(expr[i][0])-65]
                                
                            format[i] = len(expr[i])
                                    
                        else: # Not defined
                            undefined.append(i)

                
                if DEBUG and depth == 0: # show progress if debug
                    iterate = tqdm.trange(len(dict))
                else:
                    iterate = range(len(dict))
                    
                for i in iterate:
                    word = dict[i]
                    
                    split = self._splitter(word, format)
                    if split == []:
                        continue

                    self.qat_current_answer[depth][0] = word

                    for case in split:
                        # Build new expr
                        valid = True
                        expr_new = expr[:]  # Shallow copy
                        defined = []
                        defined_val = []
                        for i in range(len(expr)):
                            if expr[i][0] in ULETTER or expr[i] == "@":
                                if expr[i] == "@":
                                    valid = valid and self._indict(case[i])
                                    
                                elif expr_new[i][0] in defined:
                                    compare_string = defined_val[defined.index(expr_new[i][0])]
                                    
                                    if expr_new[i][-1] == '"': # voice
                                        compare_string = self._voice(compare_string)
                                        if compare_string == "#": # Error
                                            valid = False
                                    elif expr_new[i][-1] == '\'': # semi-voice
                                        compare_string = self._semi_voice(compare_string)
                                        if compare_string == "#": # Error
                                            valid = False
                                            
                                    if case[i] != compare_string:
                                        valid = False

                                elif i in undefined:
                                    defined.append(expr_new[i][0])
                                    
                                    if expr_new[i][-1] == '"': # un-voice
                                        defined_val.append(self._un_voice(case[i]))
                                        if defined_val[-1] == '#': # ERROR
                                            valid = False # No need to pop the defined_val
                                            
                                    elif expr_new[i][-1] == '\'': # un-semi-voice
                                        defined_val.append(self._un_semi_voice(case[i]))
                                        if defined_val[-1] == '#': # ERROR
                                            valid = False
                                            
                                    else:
                                        defined_val.append(case[i])
                                
                                if valid == False:
                                    break

                                expr_new[i] = case[i]

                        if not valid:
                            continue

                        if self._nfm("".join(expr_new), word) == True: # Match
                            # Update current letters
                            for i in undefined:
                                if expr[i][-1] == '"': # voice
                                    self.qat_current_letters[ord(expr[i][0])-65] = self._un_voice(expr_new[i])
                                elif expr[i][-1] == '\'': # semi-voice
                                    self.qat_current_letters[ord(expr[i][0])-65] = self._un_semi_voice(expr_new[i])
                                else:
                                    self.qat_current_letters[ord(expr[i][0])-65] = expr_new[i]

                            self._qat(depth + 1)

                            # Rollback current letters
                            for i in undefined:
                                self.qat_current_letters[ord(expr[i][0])-65] = ""
                        
                    if self.stop:
                        return
                    

    #%% Search (Main Processing)

    # Search
    def search(self, expr: str, num: int = 200, functions: list = []) -> str:
        self._setup_qat()
        
        # QAT?
        expr_nofunc = expr
        for item in functions:
            expr_nofunc = expr_nofunc.replace(item[0], "")
        qat_chance = sum([i in ULETTER.union(';') for i in expr_nofunc])
        
        # Empty
        if expr == "":
            return self._error("empty")
        
        # Functions
        if '%' in expr:
            return self._error("syntax", ex="Invalid %")
        
        for item in functions:
            expr = expr.replace(item[0], f"%{item[0]}%")
        
        expr = self._normalize(expr)
        if expr[0] == '#': # ERR
            return expr
        
        # Only supports one-to-one functions
        for item in functions:
            if len(item[1]) != len(item[2]):
                return self._error("syntax", ex="Function invalid!")
            for c in item[1]:
                if item[1].count(c) > 1:
                    return self._error("syntax", ex="Only supports one-to-one functions.")
            for c in item[2]:
                if item[2].count(c) > 1:
                    return self._error("syntax", ex="Only supports one-to-one functions.")
                
        self.func = functions
        
        # Process
        # - Normal
        if not qat_chance :
            expr_re = self._process_normal(expr)
            dprint(f"Regex expression normal:{expr_re}")
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
            return res
        
        # - QAT QAQ
        else:
            self.qat_num_limit = num
            exprs = expr.split(";")
            self.qat_letters = [0 for i in range(26)]
            
            # Reject <>
            if "<" in expr or ">" in expr:
                return self._error("syntax", ex="< or > in QAT")
            
            # Reject global &|! - optimized check
            for expr in exprs:
                bracket_level = 0
                for char in expr:
                    if char in '([':
                        bracket_level += 1
                    elif char in ')]':
                        bracket_level -= 1
                    elif bracket_level == 0 and char in '&|!':
                        return self._error("syntax", ex=expr)
            

            # Register Letters
            for i in range(len(exprs)-1, -1, -1):
                if exprs[i] == "": # Delete Empty Expressions
                    del exprs[i]
                else:
                    while exprs[i][0] == '(' and exprs[i][-1] == ')': # Remove unnecessary ()
                        exprs[i] = exprs[i][1:-1]
                        
                    # Register Existed Letters
                    # 0 : not exist, -1 : exist
                    functioning = False
                    for j in range(len(exprs[i])):
                        if exprs[i][j] == "%":
                            functioning = not functioning
                        if not functioning  and exprs[i][j] in ULETTER:
                            self.qat_letters[ord(exprs[i][j])-65] = -1
            
            if exprs == []: # check if empty
                return self._error("empty")

            functioning = False
            # Find Length Limitation - optimized
            for i in range(len(exprs) - 1, -1, -1):
                if '=' in exprs[i]:  # Fixed Length
                    condition = exprs[i].split('=')
                    # Validate format more efficiently
                    if (len(condition) != 2 or not condition[1].isdigit() or 
                        len(condition[0]) != 3 or not condition[0].startswith('|') or 
                        not condition[0].endswith('|')):
                        return self._error("syntax", ex=exprs[i])
                    
                    letter_idx = ord(condition[0][1]) - ord('A')
                    length_val = int(condition[1])
                    
                    # Check validity
                    if not (0 <= letter_idx < 26) or not (0 < length_val < 10):
                        return self._error("syntax", ex=exprs[i])

                    if self.qat_letters[letter_idx] != -1:  # already defined
                        return self._error("syntax", ex=exprs[i])

                    self.qat_letters[letter_idx] = length_val
                    del exprs[i]  # Remove the expression
            
            if exprs == []: # check if empty
                return self._error("empty")
            
            # Sort expressions by number of uppercase letters (most first)
            qat_order = [i for i in range(len(exprs))]
            qat_order.sort(key=lambda x: sum(c.isupper() and c.isalpha() for c in exprs[x]), reverse=True)
            exprs.sort(key=lambda x: sum(c.isupper() and c.isalpha() for c in x), reverse=True)

            self.qat_exprs = [self._process_qat(i) for i in exprs]
            self.qat_current_answer = [['', qat_order[i]] for i in range(len(exprs))]

            for i in self.qat_exprs:
                if i[0] == "#": # Error
                    return i
            
            self._qat(0)

            if self.qat_error[0] == "#": # Error
                return self.qat_error
            else:
                return self.qat_answers
    
    # print the result  
    def search_print(self, expr: str, num: int = 200, functions: list = []) -> None:
        start_time = time()
        try:
            res = self.search(expr, num=num, functions=functions)
        except Exception as e:
            print(f"Unexpected Error: {str(e)}")
            return
        
        elapsed = time() - start_time
        print(f"Expr:{expr}")
        print()
        
        if functions:
            print("Functions:")
            for item in functions:
                print(f"{item[0]}: {item[1]} -> {item[2]}")
        
        print()
        
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

if __name__ == "__main__":
    import test
    test.test()