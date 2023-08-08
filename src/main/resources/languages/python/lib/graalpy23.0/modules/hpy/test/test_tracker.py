# MIT License
# 
# Copyright (c) 2021, Oracle and/or its affiliates.
# Copyright (c) 2019 pyhandle
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
NOTE: this tests are also meant to be run as PyPy "applevel" tests.

This means that global imports will NOT be visible inside the test
functions. In particular, you have to "import pytest" inside the test in order
to be able to use e.g. pytest.raises (which on PyPy will be implemented by a
"fake pytest module")
"""
from .support import HPyTest


class TestHPyTracker(HPyTest):
    def hpytracker_module(self, ops, size=0):
        return self.make_module("""
            HPyDef_METH(f, "f", f_impl, HPyFunc_VARARGS)
            static HPy f_impl(HPyContext *ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs)
            {{
                HPyTracker ht;
                HPy result = HPy_NULL;
                ht = HPyTracker_New(ctx, {size});
                if HPy_IsNull(ht) {{
                    return HPy_NULL;
                }}
                {ops}
                HPyTracker_Close(ctx, ht);
                if (HPy_IsNull(result))
                    result = HPy_Dup(ctx, ctx->h_None);
                return result;
            }}
            @EXPORT(f)
            @INIT
        """.format(ops=ops, size=size))

    def test_new_and_free(self):
        mod = self.hpytracker_module(ops="")
        mod.f()

    def test_new_with_size_and_free(self):
        mod = self.hpytracker_module(ops="", size=10)
        mod.f()

    def test_add_and_free(self):
        mod = self.hpytracker_module(ops="""
            HPyTracker_Add(ctx, ht, HPy_Dup(ctx, args[0]));
        """)
        mod.f(5)

    def test_add_and_remove_all(self):
        mod = self.hpytracker_module(ops="""
            HPyTracker_Add(ctx, ht, args[0]);
            HPyTracker_ForgetAll(ctx, ht);
        """)
        assert mod.f(5) is None

    def test_remove_all_on_nothing(self):
        mod = self.hpytracker_module(ops="""
            HPyTracker_ForgetAll(ctx, ht);
        """)
        assert mod.f() is None

    def test_squares_example(self):
        import pytest
        mod = self.make_module("""
            HPyDef_METH(squares, "squares", squares_impl, HPyFunc_VARARGS)
            static HPy squares_impl(HPyContext *ctx, HPy self,
                              HPy *args, HPy_ssize_t nargs)
            {
                long i, n;
                long n_err = -1; // simulate an error at the given index
                int result;
                HPy key, value;
                HPyTracker ht;

                if (!HPyArg_Parse(ctx, NULL, args, nargs, "l|l", &n, &n_err))
                    return HPy_NULL;

                ht = HPyTracker_New(ctx, 0);  // track key-value pairs
                if HPy_IsNull(ht)
                    return HPy_NULL;

                HPy dict = HPyDict_New(ctx);
                if (HPy_IsNull(dict))
                    goto error;

                for (i=1; i<=n; i++) {
                    if (i==n_err)
                        goto error;
                    key = HPyLong_FromLong(ctx, i);
                    if (HPy_IsNull(key))
                        goto error;
                    if (HPyTracker_Add(ctx, ht, key) < 0)
                        goto error;
                    value = HPyLong_FromLong(ctx, i * i);
                    if (HPy_IsNull(value))
                        goto error;
                    if (HPyTracker_Add(ctx, ht, value) < 0)
                        goto error;
                    result = HPy_SetItem(ctx, dict, key, value);
                    if (result < 0)
                        goto error;
                }

                HPyTracker_Close(ctx, ht);
                return dict;

                error:
                    HPyTracker_Close(ctx, ht);
                    HPy_Close(ctx, dict);
                    HPyErr_SetString(ctx, ctx->h_ValueError, "Failed!");
                    return HPy_NULL;
            }
            @EXPORT(squares)
            @INIT
        """)
        assert mod.squares(5) == {1: 1, 2: 4, 3: 9, 4: 16, 5: 25}
        assert mod.squares(100) == dict((i, i**2) for i in range(1, 101))
        with pytest.raises(ValueError) as err:
            mod.squares(5, 3)
        assert str(err.value) == "Failed!"
