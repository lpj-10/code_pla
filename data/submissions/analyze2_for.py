__obf_state__ = globals().setdefault('__obf_state__', {})
if True:
    __obf_c_48 = 29
    __obf_state__['h___obf_c_48'] = __obf_state__.get('h___obf_c_48', 0
        ) ^ hash(__obf_c_48)
if True:
    __obf_c_49 = 375
    __obf_state__['h___obf_c_49'] = __obf_state__.get('h___obf_c_49', 0
        ) ^ hash(__obf_c_49)
if True:
    __obf_c_50 = 200
    if hash(id(__obf_c_50)) & 1 == 0:
        __obf_state__['db___obf_c_50'] = __obf_state__.get('db___obf_c_50', 0
            ) + 1
import time
__obf_state__ = globals().setdefault('__obf_state__', {})


def safe_bind(obj, name=None, index=None):
    try:
        if True:
            __obf_c_0 = 306
            __obf_state__['h___obf_c_0'] = __obf_state__.get('h___obf_c_0', 0
                ) ^ hash(__obf_c_0)
        if True:
            __obf_c_1 = 659
            __obf_state__['h___obf_c_1'] = __obf_state__.get('h___obf_c_1', 0
                ) ^ hash(__obf_c_1)
        if True:
            __obf_c_2 = 64
            if hash(id(__obf_c_2)) & 1 == 0:
                __obf_state__['db___obf_c_2'] = __obf_state__.get(
                    'db___obf_c_2', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 3) ^ id('safe_bind')) & 4294967295
        finally:
            pass
        __obf_src_0 = """def __obf_inner_0(obj, name=None, index=None):
    try:
        if index is not None:
            if hasattr(obj, '__match_args__'):
                return getattr(obj, obj.__match_args__[index])
            return obj[index]
        elif name is not None:
            return getattr(obj, name)
        return obj
    except Exception:
        return None
"""
        __obf_loc_0 = {}
        exec(__obf_src_0, globals(), __obf_loc_0)
        try:
            return __obf_loc_0['__obf_inner_0'](obj, name, index)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_safe_bind'] = 'ExceptionTriggered'


def _hidden_op_0(x, y):
    try:
        if True:
            __obf_c_3 = 389
            __obf_state__['h___obf_c_3'] = __obf_state__.get('h___obf_c_3', 0
                ) ^ hash(__obf_c_3)
        if True:
            __obf_c_4 = 266
            __obf_state__['h___obf_c_4'] = __obf_state__.get('h___obf_c_4', 0
                ) ^ hash(__obf_c_4)
        if True:
            __obf_c_5 = 913
            if hash(id(__obf_c_5)) & 1 == 0:
                __obf_state__['db___obf_c_5'] = __obf_state__.get(
                    'db___obf_c_5', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 2) ^ id('_hidden_op_0')) & 4294967295
        finally:
            pass
        __obf_src_1 = """def __obf_inner_1(x, y):
    st = globals().setdefault('__obf_state__', {})
    st['_opcnt'] = st.get('_opcnt', 0) + 1
    return x + y
"""
        __obf_loc_1 = {}
        exec(__obf_src_1, globals(), __obf_loc_1)
        try:
            return __obf_loc_1['__obf_inner_1'](x, y)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_0'] = 'ExceptionTriggered'


def _hidden_op_1(x, y):
    try:
        if True:
            __obf_c_6 = 800
            __obf_state__['h___obf_c_6'] = __obf_state__.get('h___obf_c_6', 0
                ) ^ hash(__obf_c_6)
        if True:
            __obf_c_7 = 512
            __obf_state__['h___obf_c_7'] = __obf_state__.get('h___obf_c_7', 0
                ) ^ hash(__obf_c_7)
        if True:
            __obf_c_8 = 868
            if hash(id(__obf_c_8)) & 1 == 0:
                __obf_state__['db___obf_c_8'] = __obf_state__.get(
                    'db___obf_c_8', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 2) ^ id('_hidden_op_1')) & 4294967295
        finally:
            pass
        __obf_src_2 = """def __obf_inner_2(x, y):
    st = globals().setdefault('__obf_state__', {})
    st['_opcnt'] = st.get('_opcnt', 0) + 1
    return x - y
"""
        __obf_loc_2 = {}
        exec(__obf_src_2, globals(), __obf_loc_2)
        try:
            return __obf_loc_2['__obf_inner_2'](x, y)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_1'] = 'ExceptionTriggered'


def _hidden_op_2(x, y):
    try:
        if True:
            __obf_c_9 = 910
            __obf_state__['h___obf_c_9'] = __obf_state__.get('h___obf_c_9', 0
                ) ^ hash(__obf_c_9)
        if True:
            __obf_c_10 = 33
            __obf_state__['h___obf_c_10'] = __obf_state__.get('h___obf_c_10', 0
                ) ^ hash(__obf_c_10)
        if True:
            __obf_c_11 = 80
            if hash(id(__obf_c_11)) & 1 == 0:
                __obf_state__['db___obf_c_11'] = __obf_state__.get(
                    'db___obf_c_11', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 2) ^ id('_hidden_op_2')) & 4294967295
        finally:
            pass
        __obf_src_3 = """def __obf_inner_3(x, y):
    st = globals().setdefault('__obf_state__', {})
    st['_opcnt'] = st.get('_opcnt', 0) + 1
    return x * y
"""
        __obf_loc_3 = {}
        exec(__obf_src_3, globals(), __obf_loc_3)
        try:
            return __obf_loc_3['__obf_inner_3'](x, y)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_2'] = 'ExceptionTriggered'


def _hidden_op_3(x, y):
    try:
        if True:
            __obf_c_12 = 176
            __obf_state__['h___obf_c_12'] = __obf_state__.get('h___obf_c_12', 0
                ) ^ hash(__obf_c_12)
        if True:
            __obf_c_13 = 559
            __obf_state__['h___obf_c_13'] = __obf_state__.get('h___obf_c_13', 0
                ) ^ hash(__obf_c_13)
        if True:
            __obf_c_14 = 393
            if hash(id(__obf_c_14)) & 1 == 0:
                __obf_state__['db___obf_c_14'] = __obf_state__.get(
                    'db___obf_c_14', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 2) ^ id('_hidden_op_3')) & 4294967295
        finally:
            pass
        __obf_src_4 = """def __obf_inner_4(x, y):
    st = globals().setdefault('__obf_state__', {})
    st['_opcnt'] = st.get('_opcnt', 0) + 1
    return x - y
"""
        __obf_loc_4 = {}
        exec(__obf_src_4, globals(), __obf_loc_4)
        try:
            return __obf_loc_4['__obf_inner_4'](x, y)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_3'] = 'ExceptionTriggered'


def _hidden_op_4(x, y):
    try:
        if True:
            __obf_c_15 = 621
            __obf_state__['h___obf_c_15'] = __obf_state__.get('h___obf_c_15', 0
                ) ^ hash(__obf_c_15)
        if True:
            __obf_c_16 = 839
            __obf_state__['h___obf_c_16'] = __obf_state__.get('h___obf_c_16', 0
                ) ^ hash(__obf_c_16)
        if True:
            __obf_c_17 = 948
            if hash(id(__obf_c_17)) & 1 == 0:
                __obf_state__['db___obf_c_17'] = __obf_state__.get(
                    'db___obf_c_17', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 2) ^ id('_hidden_op_4')) & 4294967295
        finally:
            pass
        __obf_src_5 = """def __obf_inner_5(x, y):
    st = globals().setdefault('__obf_state__', {})
    st['_opcnt'] = st.get('_opcnt', 0) + 1
    return x + y
"""
        __obf_loc_5 = {}
        exec(__obf_src_5, globals(), __obf_loc_5)
        try:
            return __obf_loc_5['__obf_inner_5'](x, y)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_4'] = 'ExceptionTriggered'


def _hidden_op_5(x, y):
    try:
        if True:
            __obf_c_18 = 745
            __obf_state__['h___obf_c_18'] = __obf_state__.get('h___obf_c_18', 0
                ) ^ hash(__obf_c_18)
        if True:
            __obf_c_19 = 162
            __obf_state__['h___obf_c_19'] = __obf_state__.get('h___obf_c_19', 0
                ) ^ hash(__obf_c_19)
        if True:
            __obf_c_20 = 117
            if hash(id(__obf_c_20)) & 1 == 0:
                __obf_state__['db___obf_c_20'] = __obf_state__.get(
                    'db___obf_c_20', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 2) ^ id('_hidden_op_5')) & 4294967295
        finally:
            pass
        __obf_src_6 = """def __obf_inner_6(x, y):
    st = globals().setdefault('__obf_state__', {})
    st['_opcnt'] = st.get('_opcnt', 0) + 1
    return x * y
"""
        __obf_loc_6 = {}
        exec(__obf_src_6, globals(), __obf_loc_6)
        try:
            return __obf_loc_6['__obf_inner_6'](x, y)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_5'] = 'ExceptionTriggered'


def _hidden_op_6(x, y):
    try:
        if True:
            __obf_c_21 = 675
            __obf_state__['h___obf_c_21'] = __obf_state__.get('h___obf_c_21', 0
                ) ^ hash(__obf_c_21)
        if True:
            __obf_c_22 = 865
            __obf_state__['h___obf_c_22'] = __obf_state__.get('h___obf_c_22', 0
                ) ^ hash(__obf_c_22)
        if True:
            __obf_c_23 = 820
            if hash(id(__obf_c_23)) & 1 == 0:
                __obf_state__['db___obf_c_23'] = __obf_state__.get(
                    'db___obf_c_23', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 2) ^ id('_hidden_op_6')) & 4294967295
        finally:
            pass
        __obf_src_7 = """def __obf_inner_7(x, y):
    st = globals().setdefault('__obf_state__', {})
    st['_opcnt'] = st.get('_opcnt', 0) + 1
    return x + y
"""
        __obf_loc_7 = {}
        exec(__obf_src_7, globals(), __obf_loc_7)
        try:
            return __obf_loc_7['__obf_inner_7'](x, y)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_6'] = 'ExceptionTriggered'


def _hidden_op_7(x, y):
    try:
        if True:
            __obf_c_24 = 370
            __obf_state__['h___obf_c_24'] = __obf_state__.get('h___obf_c_24', 0
                ) ^ hash(__obf_c_24)
        if True:
            __obf_c_25 = 75
            __obf_state__['h___obf_c_25'] = __obf_state__.get('h___obf_c_25', 0
                ) ^ hash(__obf_c_25)
        if True:
            __obf_c_26 = 544
            if hash(id(__obf_c_26)) & 1 == 0:
                __obf_state__['db___obf_c_26'] = __obf_state__.get(
                    'db___obf_c_26', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 2) ^ id('_hidden_op_7')) & 4294967295
        finally:
            pass
        __obf_src_8 = """def __obf_inner_8(x, y):
    st = globals().setdefault('__obf_state__', {})
    st['_opcnt'] = st.get('_opcnt', 0) + 1
    return x * y
"""
        __obf_loc_8 = {}
        exec(__obf_src_8, globals(), __obf_loc_8)
        try:
            return __obf_loc_8['__obf_inner_8'](x, y)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_7'] = 'ExceptionTriggered'


c_0 = (lambda : 42)()
c_1 = (lambda : 'Basic:')()
c_2 = (lambda : 2)()
c_3 = (lambda : 3)()
c_4 = (lambda : 4)()
c_5 = (lambda : 5)()
c_6 = (lambda : 10)()
c_7 = (lambda : 'x')()
c_8 = (lambda : 'y')()
c_9 = (lambda : 'Loop total:')()
c_10 = (lambda : 'One')()
c_11 = (lambda : 'Two')()
c_12 = (lambda : 'Three')()
c_13 = (lambda : 'Other')()
c_14 = (lambda : 'x is two or three')()
c_15 = (lambda : 'Matched sequence [1,2,3]')()
c_16 = (lambda : 'Default case')()
c_17 = (lambda : 'Live branch')()
c_18 = (lambda : 'Dead branch')()
c_19 = (lambda : 'Start integrated test')()
c_20 = (lambda : 15)()
c_21 = (lambda : '__main__')()
GLOBAL_CONST = c_0


def basic_test(a, b):
    try:
        if True:
            __obf_c_27 = 228
            __obf_state__['h___obf_c_27'] = __obf_state__.get('h___obf_c_27', 0
                ) ^ hash(__obf_c_27)
        if True:
            __obf_c_28 = 521
            __obf_state__['h___obf_c_28'] = __obf_state__.get('h___obf_c_28', 0
                ) ^ hash(__obf_c_28)
        if True:
            __obf_c_29 = 388
            if hash(id(__obf_c_29)) & 1 == 0:
                __obf_state__['db___obf_c_29'] = __obf_state__.get(
                    'db___obf_c_29', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 2) ^ id('basic_test')) & 4294967295
        finally:
            pass
        __obf_src_9 = """def __obf_inner_9(a, b):
    c = _hidden_op_0(a, b) if a > b else _hidden_op_1(a, b)
    d = _hidden_op_4(_hidden_op_2(a, b), _hidden_op_3(GLOBAL_CONST, c))
    print(c_1, d)
    return d
"""
        __obf_loc_9 = {}
        exec(__obf_src_9, globals(), __obf_loc_9)
        try:
            return __obf_loc_9['__obf_inner_9'](a, b)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_basic_test'] = 'ExceptionTriggered'


def loop_test():
    try:
        if True:
            __obf_c_30 = 695
            __obf_state__['h___obf_c_30'] = __obf_state__.get('h___obf_c_30', 0
                ) ^ hash(__obf_c_30)
        if True:
            __obf_c_31 = 315
            __obf_state__['h___obf_c_31'] = __obf_state__.get('h___obf_c_31', 0
                ) ^ hash(__obf_c_31)
        if True:
            __obf_c_32 = 869
            if hash(id(__obf_c_32)) & 1 == 0:
                __obf_state__['db___obf_c_32'] = __obf_state__.get(
                    'db___obf_c_32', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 0) ^ id('loop_test')) & 4294967295
        finally:
            pass
        __obf_src_10 = """def __obf_inner_10():
    nums = [1, c_2, c_3, c_4]
    total = 0
    if True:
        _completed_flag_0 = True
        _iter_var_0 = iter(range(c_5))
        while True:
            try:
                i = next(_iter_var_0)
            except StopIteration:
                break
            total = total + i
    if True:
        _completed_flag_1 = True
        _iter_var_1 = iter(range(c_6, 0, -c_2))
        while True:
            try:
                i = next(_iter_var_1)
            except StopIteration:
                break
            total = total + i
    if True:
        _completed_flag_2 = True
        _iter_var_2 = iter(reversed(range(c_3)))
        while True:
            try:
                i = next(_iter_var_2)
            except StopIteration:
                break
            total = total + i
    if True:
        _completed_flag_3 = True
        _iter_var_3 = iter(zip(nums, range(c_4)))
        while True:
            try:
                a, b = next(_iter_var_3)
            except StopIteration:
                break
            total = total + _hidden_op_5(a, b)
    if True:
        _completed_flag_4 = True
        _iter_var_4 = iter(enumerate(nums))
        while True:
            try:
                idx, val = next(_iter_var_4)
            except StopIteration:
                break
            total = total + _hidden_op_6(idx, val)
    d = {c_7: 1, c_8: c_2}
    if True:
        _completed_flag_5 = True
        _iter_var_5 = iter(d.items())
        while True:
            try:
                key, val = next(_iter_var_5)
            except StopIteration:
                break
            total = total + val
    print(c_9, total)
    return total
"""
        __obf_loc_10 = {}
        exec(__obf_src_10, globals(), __obf_loc_10)
        try:
            return __obf_loc_10['__obf_inner_10']()
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_loop_test'] = 'ExceptionTriggered'


def control_flow_flatten(x):
    try:
        if True:
            __obf_c_33 = 577
            __obf_state__['h___obf_c_33'] = __obf_state__.get('h___obf_c_33', 0
                ) ^ hash(__obf_c_33)
        if True:
            __obf_c_34 = 473
            __obf_state__['h___obf_c_34'] = __obf_state__.get('h___obf_c_34', 0
                ) ^ hash(__obf_c_34)
        if True:
            __obf_c_35 = 768
            if hash(id(__obf_c_35)) & 1 == 0:
                __obf_state__['db___obf_c_35'] = __obf_state__.get(
                    'db___obf_c_35', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 1) ^ id('control_flow_flatten')
                ) & 4294967295
        finally:
            pass
        __obf_src_11 = """def __obf_inner_11(x):
    if x == 1:
        print(c_10)
    elif x == c_2:
        print(c_11)
    elif x == c_3:
        print(c_12)
    else:
        print(c_13)
    return _hidden_op_7(x, c_2)
"""
        __obf_loc_11 = {}
        exec(__obf_src_11, globals(), __obf_loc_11)
        try:
            return __obf_loc_11['__obf_inner_11'](x)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_control_flow_flatten'] = 'ExceptionTriggered'


class Point:

    def __init__(self, x, y):
        try:
            if True:
                __obf_c_36 = 812
                __obf_state__['h___obf_c_36'] = __obf_state__.get(
                    'h___obf_c_36', 0) ^ hash(__obf_c_36)
            if True:
                __obf_c_37 = 403
                __obf_state__['h___obf_c_37'] = __obf_state__.get(
                    'h___obf_c_37', 0) ^ hash(__obf_c_37)
            if True:
                __obf_c_38 = 167
                if hash(id(__obf_c_38)) & 1 == 0:
                    __obf_state__['db___obf_c_38'] = __obf_state__.get(
                        'db___obf_c_38', 0) + 1
            try:
                __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 +
                    (hash(time.time()) ^ 3) ^ id('__init__')) & 4294967295
            finally:
                pass
            __obf_src_12 = (
                'def __obf_inner_12(self, x, y):\n    self.x = x\n    self.y = y\n'
                )
            __obf_loc_12 = {}
            exec(__obf_src_12, globals(), __obf_loc_12)
            try:
                return __obf_loc_12['__obf_inner_12'](self, x, y)
            except:
                globals()['_exc_return_block'] = 'ExceptionTriggered'
        except:
            globals()['_exc___init__'] = 'ExceptionTriggered'


def test_match(obj):
    try:
        if True:
            __obf_c_39 = 523
            __obf_state__['h___obf_c_39'] = __obf_state__.get('h___obf_c_39', 0
                ) ^ hash(__obf_c_39)
        if True:
            __obf_c_40 = 572
            __obf_state__['h___obf_c_40'] = __obf_state__.get('h___obf_c_40', 0
                ) ^ hash(__obf_c_40)
        if True:
            __obf_c_41 = 645
            if hash(id(__obf_c_41)) & 1 == 0:
                __obf_state__['db___obf_c_41'] = __obf_state__.get(
                    'db___obf_c_41', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 1) ^ id('test_match')) & 4294967295
        finally:
            pass
        __obf_src_13 = """def __obf_inner_13(obj):
    if True:
        x = None
        z = None
        y = None
        if obj in (c_2, c_3):
            print(c_14)
        elif isinstance(obj, Point):
            y = safe_bind(obj, name='y')
            print(f'Point with x=None, y={y}')
        elif isinstance(obj, int):
            x = obj
            if x > c_6:
                print(f'Integer greater than 10: {x}')
        elif isinstance(obj, (list, tuple)) and len(obj) == 3:
            x = safe_bind(obj, index=0)
            y = safe_bind(obj, index=1)
            z = safe_bind(obj, index=2)
            if len([x, y, z]) == c_3:
                print(c_15)
        else:
            print(c_16)
"""
        __obf_loc_13 = {}
        exec(__obf_src_13, globals(), __obf_loc_13)
        try:
            return __obf_loc_13['__obf_inner_13'](obj)
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_test_match'] = 'ExceptionTriggered'


def dead_code_test():
    try:
        if True:
            __obf_c_42 = 688
            __obf_state__['h___obf_c_42'] = __obf_state__.get('h___obf_c_42', 0
                ) ^ hash(__obf_c_42)
        if True:
            __obf_c_43 = 202
            __obf_state__['h___obf_c_43'] = __obf_state__.get('h___obf_c_43', 0
                ) ^ hash(__obf_c_43)
        if True:
            __obf_c_44 = 45
            if hash(id(__obf_c_44)) & 1 == 0:
                __obf_state__['db___obf_c_44'] = __obf_state__.get(
                    'db___obf_c_44', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 0) ^ id('dead_code_test')) & 4294967295
        finally:
            pass
        __obf_src_14 = """def __obf_inner_14():
    x = c_6
    if x > c_5:
        print(c_17)
    else:
        print(c_18)
    return x
"""
        __obf_loc_14 = {}
        exec(__obf_src_14, globals(), __obf_loc_14)
        try:
            return __obf_loc_14['__obf_inner_14']()
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_dead_code_test'] = 'ExceptionTriggered'


def integrated_test():
    try:
        if True:
            __obf_c_45 = 23
            __obf_state__['h___obf_c_45'] = __obf_state__.get('h___obf_c_45', 0
                ) ^ hash(__obf_c_45)
        if True:
            __obf_c_46 = 371
            __obf_state__['h___obf_c_46'] = __obf_state__.get('h___obf_c_46', 0
                ) ^ hash(__obf_c_46)
        if True:
            __obf_c_47 = 586
            if hash(id(__obf_c_47)) & 1 == 0:
                __obf_state__['db___obf_c_47'] = __obf_state__.get(
                    'db___obf_c_47', 0) + 1
        try:
            __obf_state__['_mix'] = (__obf_state__.get('_mix', 0) * 131 + (
                hash(time.time()) ^ 0) ^ id('integrated_test')) & 4294967295
        finally:
            pass
        __obf_src_15 = """def __obf_inner_15():
    print(c_19)
    v1 = basic_test(c_5, c_3)
    v2 = loop_test()
    v3 = control_flow_flatten(c_3)
    test_match(Point(None, c_2))
    test_match(c_3)
    test_match(c_20)
    test_match([1, c_2, c_3])
    v4 = dead_code_test()
    print(v1)
"""
        __obf_loc_15 = {}
        exec(__obf_src_15, globals(), __obf_loc_15)
        try:
            return __obf_loc_15['__obf_inner_15']()
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_integrated_test'] = 'ExceptionTriggered'


if __name__ == c_21:
    integrated_test()