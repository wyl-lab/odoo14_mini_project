#!/usr/bin/env python
# -*- coding: latin-1 -*-

from .py3k import PY3K, basestring, unicode

# fpdf php helpers:

def substr(s, start, length=-1):
       if length < 0:
               length=len(s)-start
       return s[start:start+length]

def sprintf(fmt, *args): return fmt % args

def print_r(array):
    if not isinstance(array, dict):
        array = dict([(k, k) for k in array])
    for k, v in array.items():
        print("[%s] => %s " % (k, v))
        
def StrToUTF16BE(instr, setbom=True):
    "Converts string to UTF16-BE."
    outstr = b''
    if (setbom):
        outstr += b'\xFE\xFF'
    if not isinstance(instr, unicode):
        instr = instr.decode('UTF-8')
    outstr += instr.encode('UTF-16BE')
    return outstr

def StringToArray(instr):
    "Converts string to codepoints array"
    return [ord(c) for c in instr]

# ttfints php helpers:    

def die(msg):
    raise RuntimeError(msg)
    
def str_repeat(s, count):
    return s * count
    
def str_pad(s, pad_length=0, pad_char= " ", pad_type= +1 ):
    if pad_type<0: # pad left
        return s.rjust(pad_length, pad_char)
    elif pad_type>0: # pad right
        return s.ljust(pad_length, pad_char)
    else: # pad both
        return s.center(pad_length, pad_char)

strlen = count = lambda s: len(s)
