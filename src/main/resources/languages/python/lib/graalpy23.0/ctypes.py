# Copyright (c) 2018, 2021, Oracle and/or its affiliates. All rights reserved.
# DO NOT ALTER OR REMOVE COPYRIGHT NOTICES OR THIS FILE HEADER.
#
# The Universal Permissive License (UPL), Version 1.0
#
# Subject to the condition set forth below, permission is hereby granted to any
# person obtaining a copy of this software, associated documentation and/or
# data (collectively the "Software"), free of charge and under any and all
# copyright rights in the Software, and any and all patent rights owned or
# freely licensable by each licensor hereunder covering either (i) the
# unmodified Software as contributed to or provided by such licensor, or (ii)
# the Larger Works (as defined below), to deal in both
#
# (a) the Software, and
#
# (b) any piece of software and/or hardware listed in the lrgrwrks.txt file if
# one is included with the Software each a "Larger Work" to which the Software
# is contributed by such licensors),
#
# without restriction, including without limitation the rights to copy, create
# derivative works of, display, perform, and distribute the Software and make,
# use, sell, offer for sale, import, export, have made, and have sold the
# Software and the Larger Work(s), and to sublicense the foregoing rights on
# either these or other terms.
#
# This license is subject to the following condition:
#
# The above copyright notice and either this complete permission notice or at a
# minimum a reference to the UPL must be included in all copies or substantial
# portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Taken from pypy
class CDLL(object):
    """An instance of this class represents a loaded dll/shared
    library, exporting functions using the standard C calling
    convention (named 'cdecl' on Windows).

    The exported functions can be accessed as attributes, or by
    indexing with the function name.  Examples:

    <obj>.qsort -> callable object
    <obj>['qsort'] -> callable object

    Calling the functions releases the Python GIL during the call and
    reacquires it afterwards.
    """
    def __init__(self, name, mode=0, handle=None,
                 use_errno=False,
                 use_last_error=False):
        # TODO
        pass



# Dummy classes:


class _CData:
    pass


class _Array(_CData):
    pass



class _SimpleCDataMetaCls(type):
    """
    Dummy implementation of the operators on _SimpleCDatan subclasses.

    For example: ctypes.c_int * 3 gives dynamically created class representing
    the type of the array.
    """

    def __mul__(self, other):
        return type(self.__name__ + '_Array_' + str(other), (_Array, object,), {})

    def __rmul__(self, other):
        return type(self.__name__ + '_Array_' + str(other), (_Array, object,), {})


class _SimpleCData(_CData, metaclass=_SimpleCDataMetaCls):
    pass


class c_void_p(_SimpleCData):
    _type_ = "P"


class c_double(_SimpleCData):
    _type_ = "d"
    
class c_float(_SimpleCData):
    _type_ = "f"

class c_int(_SimpleCData):
    _type_ = "i"


class c_int32(c_int):
    pass


class c_uint(_SimpleCData):
    _type_ = "I"


class c_uint32(c_uint):
    pass


class c_long(_SimpleCData):
    _type_ = "l"
    
class c_ulong(_SimpleCData):
    _type_ = "L"
    
class c_longlong(_SimpleCData):
    _type_ = "l"
    
class c_ulonglong(_SimpleCData):
    _type_ = "L"


class c_uint64(c_ulong):
    pass


class c_char(_SimpleCData):
    _type_ = "c"
    
class c_wchar(_SimpleCData):
    _type_ = "u"
    
class c_byte(_SimpleCData):
    _type_ = "b"
    
class c_ubyte(_SimpleCData):
    _type_ = "B"
    
class c_short(_SimpleCData):
    _type_ = "h"
    
class c_ushort(_SimpleCData):
    _type_ = "H"

class py_object(_SimpleCData):
    _type_ = "O"
    def __repr__(self):
        try:
            return super().__repr__()
        except ValueError:
            return "%s(<NULL>)" % type(self).__name__


class _CFuncPtr():
    def __init__(self, value):
        self.value = value


_c_functype_cache = {}
def CFUNCTYPE(restype, *argtypes, **kw):
    """CFUNCTYPE(restype, *argtypes,
                 use_errno=False, use_last_error=False) -> function prototype.

    restype: the result type
    argtypes: a sequence specifying the argument types

    The function prototype can be called in different ways to create a
    callable object:

    prototype(integer address) -> foreign function
    prototype(callable) -> create and return a C callable function from callable
    prototype(integer index, method name[, paramflags]) -> foreign function calling a COM method
    prototype((ordinal number, dll object)[, paramflags]) -> foreign function exported by ordinal
    prototype((function name, dll object)[, paramflags]) -> foreign function exported by name
    """
    flags = 0
    if kw.pop("use_errno", False):
        #flags |= _FUNCFLAG_USE_ERRNO
        pass
    if kw.pop("use_last_error", False):
        #flags |= _FUNCFLAG_USE_LASTERROR
        pass
    if kw:
        raise ValueError("unexpected keyword argument(s) %s" % kw.keys())
    try:
        return _c_functype_cache[(restype, argtypes, flags)]
    except KeyError:
        class CFunctionType(_CFuncPtr):
            _argtypes_ = argtypes
            _restype_ = restype
            _flags_ = flags
        _c_functype_cache[(restype, argtypes, flags)] = CFunctionType
        return CFunctionType


class _Pointer():
    def __init__(self, value):
        self.value = value


def POINTER(basetype):
    return type("LP_" + basetype.__name__, (_Pointer,), {})


def PYFUNCTYPE(restype, *argtypes):
    class CFunctionType(_CFuncPtr):
        _argtypes_ = argtypes
        _restype_ = restype
        #_flags_ = _FUNCFLAG_CDECL | _FUNCFLAG_PYTHONAPI
        _flags_ = 0
    return CFunctionType


_cast_addr = 0xFF0000000000000 << 4 # avoid freezing a constant PInt into the AST
_cast = PYFUNCTYPE(py_object, c_void_p, py_object, py_object)(_cast_addr)
def cast(obj, typ):
    return _cast(obj, obj, typ)
