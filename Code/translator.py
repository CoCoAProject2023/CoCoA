from ast import Assign
import re
from lexer import *
from tokens import *


def _findSans(tok):
    sans = re.compile(r'[a-zA-Z]*\_SANS')
    if sans.search(tok.type):
        return True
    return False


def _findSens(tok):
    sens = re.compile(r'[a-zA-Z]*\_SENS')
    if sens.search(tok.type):
        return True
    return False


def _findVarInString(tok):
    stringWVar = re.compile(r'\{(\${1}[a-zA-Z_][a-zA-Z0-9_]*)\}')
    if tok.type == "STRING_LITERAL" and stringWVar.search(tok.value):
        lista = re.split(
            r'(\{|\})', tok.value)
        lista = [i for i in lista if not re.match(
            r'(\{|\})', i)]
        tok.type = "STRING_WITH_VAR"
        tok.value = lista
        return True
    return False


stringouvar = r'(((\'|\")[a-zA-Z_][a-zA-Z0-9_]*(\'|\"))|((\$){0,1}[a-zA-Z_][a-zA-Z0-9_]*))'


def _findInputInString(tok):
    stringWInput = re.compile(
        r'\{(\$_SERVER|\$_GET|\$_POST|\$_FILES|\$_REQUEST|\$_SESSION|\$_ENV|\$_COOKIE|\$php_errormsg|\$http_response_header)\(((((\'|\")[a-zA-Z_][a-zA-Z0-9_]*(\'|\"))|((\$){0,1}[a-zA-Z_][a-zA-Z0-9_]*))(\,(((\'|\")[a-zA-Z_][a-zA-Z0-9_]*(\'|\"))|((\$){0,1}[a-zA-Z_][a-zA-Z0-9_]*))){0,1})*\)\}')
    if tok.type == "STRING_LITERAL" and stringWInput.search(tok.value):
        lista = re.split(
            r'(\{|\})', tok.value)
        lista = [i for i in lista if not re.match(
            r'(\{|\})', i)]
        tok.type = "STRING_WITH_INPUT"
        tok.value = lista
        return True
    return False


class Translator(object):

    def __init__(self):
        pass

    def translate(self, lextokens):
        ignore = {'LPAREN', 'RPAREN',
                  'LBRACE', 'RBRACE',
                  'LBRACKET', 'RBRACKET',
                  'SEMI', 'COLON', 'COMMA'}
        ops = [
            'EQUALS', 'CONCAT',
            'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',
            'OR', 'AND', 'NOT',
            'LT', 'GT', 'GE', 'LE',
            'EQ', 'NEQ']

        # LEXTOKEN PREPROCESSING
        mytokens = []  # intermediate language
        i = 0  # iterator
        var = []  # stores context to know the number of a var
        func = []  # stores context to know the number of a var
        bracecount = []  # to know if the } is closing an if/else/switch/etc
        casecount = 0  # to close each case
        call = 0  # to close a func call
        cond = 0  # to close a condition in if or switch
        assign = 0  # to close an assignment

        while i < len(lextokens):
            tok = lextokens[i]
            print(tok)
            # ignorar parametros passados numa entrypoint
            if tok.type == "INPUT" and lextokens[i+1].type == "LPAREN":
                del lextokens[i+1]
                while lextokens[i+1].value != ")":
                    del lextokens[i+1]
                del lextokens[i+1]
                continue

            # TODO
            # tratar pointers com uma so variavel
            elif tok.type == "VAR" and lextokens[i+1].type == "POINTER":
                tok.value = tok.value + "." + lextokens[i+2].value
                del lextokens[i+1]
                del lextokens[i+1]
                continue

            elif tok.type == "VAR":
                if tok.value not in var:
                    var.append(tok.value)
                mytokens.append(
                    MyToken("VAR"+str(var.index(tok.value)), tok.lineno))

            elif tok.type == "FUNC":
                bracecount.append("ENDFUNCBLOCK")
                funcname = lextokens[i+1]
                if funcname.value not in func:
                    func.append(funcname.value)
                mytokens.append(
                    MyToken("FUNC"+str(func.index(funcname.value)), funcname.lineno))
                del lextokens[i+1]

            elif tok.type == "INPUT":
                mytokens.append(
                    MyToken("INPUT", tok.lineno))
            elif tok.type in ops:
                if tok.type == "EQUALS":
                    assign = 1
                mytokens.append(
                    MyToken("OP"+str(ops.index(tok.type)), tok.lineno))
            elif tok.type == "STRING_LITERAL":
                # for cases like "ola{$a}adeus"
                if _findVarInString(tok):
                    for elem in (_ for _ in tok.value if len(tok.value) > 0):
                        if len(elem) > 0 and elem[0] == "$":
                            if elem not in var:
                                var.append(elem)
                            mytokens.append(
                                MyToken("VAR"+str(var.index(elem)), tok.lineno))
                        else:
                            mytokens.append(
                                MyToken("STRING", tok.lineno))
                    continue

                # for cases like "ola{$_GET('username')}adeus"
                if _findInputInString(tok):
                    for elem in (_ for _ in tok.value if len(tok.value) > 0):
                        if elem[0] == "$":
                            mytokens.append(
                                MyToken("INPUT", tok.lineno))
                        else:
                            mytokens.append(
                                MyToken("STRING", tok.lineno))
                    continue

                mytokens.append(MyToken("STRING", tok.lineno))

            elif tok.type == "TRY":
                bracecount.append("ENDTRY")
                mytokens.append(MyToken("TRY", tok.lineno))
            elif tok.type == "CATCH":
                bracecount.append("ENDCATCH")
                mytokens.append(MyToken("CATCH", tok.lineno))
            elif tok.type == "IF":
                bracecount.append("ENDIF")
                cond = 1
                mytokens.append(MyToken("IF", tok.lineno))
                mytokens.append(MyToken("COND", tok.lineno))
            elif tok.type == "ELSEIF":
                bracecount.append("ENDELSEIF")
                cond = 1
                mytokens.append(MyToken("ELSEIF", tok.lineno))
                mytokens.append(MyToken("COND", tok.lineno))
            elif tok.type == "ELSE":
                bracecount.append("ENDELSE")
                mytokens.append(MyToken("ELSE", tok.lineno))
            elif tok.type == "WHILE":
                bracecount.append("ENDWHILE")
                cond = 1
                mytokens.append(MyToken("WHILE", tok.lineno))
                mytokens.append(MyToken("COND", tok.lineno))
            elif tok.type == "FOR":
                bracecount.append("ENDFOR")
                cond = 1
                mytokens.append(MyToken("FOR", tok.lineno))
                mytokens.append(MyToken("COND", tok.lineno))
            elif tok.type == "SWITCH":
                bracecount.append("ENDSWITCH")
                cond = 1
                mytokens.append(MyToken("SWITCH", tok.lineno))
                mytokens.append(MyToken("COND", tok.lineno))
            elif tok.type == "CASE":
                if casecount > 0:
                    mytokens.append(
                        MyToken("ENDCASE", tok.lineno))
                    casecount -= 1
                casecount += 1
                mytokens.append(
                    MyToken("CASE", tok.lineno))
            elif tok.type == "DEFAULT":
                mytokens.append(
                    MyToken("ENDCASE", tok.lineno))
                mytokens.append(
                    MyToken("DEFAULT", tok.lineno))

            elif tok.type == "FUNC_CALL":
                call = 1
                if tok.value not in func:
                    func.append(tok.value)
                mytokens.append(
                    MyToken("FUNC"+str(func.index(tok.value)), tok.lineno))
            elif _findSans(tok) or _findSens(tok):
                call = 1
                mytokens.append(
                    MyToken(tok.type, tok.lineno))
            elif tok.type == "RBRACE":
                mytokens.append(
                    MyToken(bracecount.pop(), tok.lineno))
            elif tok.type == "RPAREN":
                if call == 1:
                    mytokens.append(
                        MyToken("END_CALL", tok.lineno))
                    call = 0
                elif cond == 1:
                    mytokens.append(
                        MyToken("END_COND", tok.lineno))
                    cond = 0
            elif tok.type == "SEMI":
                if call == 1:
                    mytokens.append(
                        MyToken("END_CALL", tok.lineno))
                    call = 0
                elif assign == 1:
                    assign = 0
                    mytokens.append(
                        MyToken("END_ASSIGN", tok.lineno))
            elif tok.type in ignore:
                pass
            else:
                mytokens.append(
                    MyToken(tok.type, tok.lineno))

            i += 1

        return mytokens[3:-2]


translator = Translator()
