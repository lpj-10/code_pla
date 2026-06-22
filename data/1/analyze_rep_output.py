import platform
import random
DEBUG_MODE = False


def _record_metric(key, val):
    try:
        try:
            m = globals().setdefault('__debug_metrics__', {})
            m[key] = (m.get(key, 0) ^ hash(val)) & 4294967295
        except Exception:
            pass
    except:
        globals()['_exc__record_metric'] = 'Error code'


if DEBUG_MODE:
    __dbg_c_5 = 530
    _record_metric('h___dbg_c_5', __dbg_c_5)
if DEBUG_MODE:
    __dbg_c_6 = 179
    _record_metric('h___dbg_c_6', __dbg_c_6)
if random.random() < 0.02 and DEBUG_MODE:
    if platform.system().lower().startswith('win'):
        _record_metric('db_rare_win', 1)
    else:
        _record_metric('db_rare_other', 1)
import time
__runtime_cache__ = globals().setdefault('__runtime_cache__', {})


def safe_bind(*args, **kwargs):
    try:
        if DEBUG_MODE:
            __dbg_c_0 = 448
            _record_metric('h___dbg_c_0', __dbg_c_0)
        if random.random() < 0.02 and DEBUG_MODE:
            if platform.system().lower().startswith('win'):
                _record_metric('db_rare_win', 1)
            else:
                _record_metric('db_rare_other', 1)
        try:
            __runtime_cache__['safe_bind'] = time.time()
        finally:
            _ = None
        __src_0 = """def __inner_0(obj, name=None, index=None):
    try:
        if index is not None:
            if hasattr(obj, '__match_args__'):
                return getattr(obj, obj.__match_args__[index])
            return obj[index]
        elif name is not None:
            return getattr(obj, name)
        return obj
    except Exception:
        return None"""
        __cache_0 = globals().setdefault('__cache_0', {})
        if '__inner_0' not in __cache_0:
            exec(__src_0, globals(), __cache_0)
        try:
            return __cache_0['__inner_0'](*args, **kwargs)
        except:
            globals()['_exc_return_block'] = 'Error code'
    except:
        globals()['_exc_safe_bind'] = 'Error code'


def _hidden_op_0(*args, **kwargs):
    try:
        if DEBUG_MODE:
            __dbg_c_1 = 555
            _record_metric('h___dbg_c_1', __dbg_c_1)
        if random.random() < 0.02 and DEBUG_MODE:
            if platform.system().lower().startswith('win'):
                _record_metric('db_rare_win', 1)
            else:
                _record_metric('db_rare_other', 1)
        try:
            __runtime_cache__['_hidden_op_0'] = time.time()
        finally:
            _ = None
        __src_1 = """def __inner_1(x, y):
    st = globals().setdefault('__obf_state__', {})
    st['_opcnt'] = st.get('_opcnt', 0) + 1
    return x / y"""
        __cache_1 = globals().setdefault('__cache_1', {})
        if '__inner_1' not in __cache_1:
            exec(__src_1, globals(), __cache_1)
        try:
            return __cache_1['__inner_1'](*args, **kwargs)
        except:
            globals()['_exc_return_block'] = 'Error code'
    except:
        globals()['_exc__hidden_op_0'] = 'Error code'


c_0 = (lambda : 90)()
c_1 = (lambda : 'A')()
c_2 = (lambda : 75)()
c_3 = (lambda : 'B')()
c_4 = (lambda : 60)()
c_5 = (lambda : 'C')()
c_6 = (lambda : 'D')()
c_7 = (lambda : '=== Student Report ===')()
c_8 = (lambda : '======================')()
c_9 = (lambda : 'Alice')()
c_10 = (lambda : 'Bob')()
c_11 = (lambda : 'Charlie')()
c_12 = (lambda : 'Daisy')()
c_13 = (lambda : 92)()
c_14 = (lambda : 85)()
c_15 = (lambda : 70)()
c_16 = (lambda : 65)()
c_17 = (lambda : 68)()
c_18 = (lambda : 88)()
c_19 = (lambda : 94)()
c_20 = (lambda : 91)()
c_21 = (lambda : 55)()
c_22 = (lambda : 58)()
import math


def compute_average(*args, **kwargs):
    try:
        if DEBUG_MODE:
            __dbg_c_2 = 358
            _record_metric('h___dbg_c_2', __dbg_c_2)
        if random.random() < 0.02 and DEBUG_MODE:
            if platform.system().lower().startswith('win'):
                _record_metric('db_rare_win', 1)
            else:
                _record_metric('db_rare_other', 1)
        try:
            __runtime_cache__['compute_average'] = time.time()
        finally:
            _ = None
        __src_2 = """def __inner_2(scores):
    total = 0
    if True:
        _completed_flag_0 = True
        _iter_var_0 = iter(scores)
        while True:
            try:
                s = next(_iter_var_0)
            except StopIteration:
                break
            total = total + s
    return _hidden_op_0(total, len(scores))"""
        __cache_2 = globals().setdefault('__cache_2', {})
        if '__inner_2' not in __cache_2:
            exec(__src_2, globals(), __cache_2)
        try:
            return __cache_2['__inner_2'](*args, **kwargs)
        except:
            globals()['_exc_return_block'] = 'Error code'
    except:
        globals()['_exc_compute_average'] = 'Error code'


def grade_students(*args, **kwargs):
    try:
        if DEBUG_MODE:
            __dbg_c_3 = 555
            _record_metric('h___dbg_c_3', __dbg_c_3)
        if random.random() < 0.02 and DEBUG_MODE:
            if platform.system().lower().startswith('win'):
                _record_metric('db_rare_win', 1)
            else:
                _record_metric('db_rare_other', 1)
        try:
            __runtime_cache__['grade_students'] = time.time()
        finally:
            _ = None
        __src_3 = """def __inner_3(students):
    results = []
    if True:
        _completed_flag_1 = True
        _iter_var_1 = iter(students.items())
        while True:
            try:
                name, scores = next(_iter_var_1)
            except StopIteration:
                break
            avg = compute_average(scores)
            if avg >= c_0:
                level = c_1
            elif avg >= c_2:
                level = c_3
            elif avg >= c_4:
                level = c_5
            else:
                level = c_6
            results.append((name, level, avg))
    return results"""
        __cache_3 = globals().setdefault('__cache_3', {})
        if '__inner_3' not in __cache_3:
            exec(__src_3, globals(), __cache_3)
        try:
            return __cache_3['__inner_3'](*args, **kwargs)
        except:
            globals()['_exc_return_block'] = 'Error code'
    except:
        globals()['_exc_grade_students'] = 'Error code'


def display_report(*args, **kwargs):
    try:
        if DEBUG_MODE:
            __dbg_c_4 = 573
            _record_metric('h___dbg_c_4', __dbg_c_4)
        if random.random() < 0.02 and DEBUG_MODE:
            if platform.system().lower().startswith('win'):
                _record_metric('db_rare_win', 1)
            else:
                _record_metric('db_rare_other', 1)
        try:
            __runtime_cache__['display_report'] = time.time()
        finally:
            _ = None
        __src_4 = """def __inner_4(data):
    print(c_7)
    if True:
        _completed_flag_2 = True
        _iter_var_2 = iter(data)
        while True:
            try:
                name, level, avg = next(_iter_var_2)
            except StopIteration:
                break
            print(f'{name}: {avg:.2f} ({level})')
    print(c_8)"""
        __cache_4 = globals().setdefault('__cache_4', {})
        if '__inner_4' not in __cache_4:
            exec(__src_4, globals(), __cache_4)
        try:
            return __cache_4['__inner_4'](*args, **kwargs)
        except:
            globals()['_exc_return_block'] = 'Error code'
    except:
        globals()['_exc_display_report'] = 'Error code'


students = {c_9: [c_0, c_13, c_14], c_10: [c_15, c_16, c_17], c_11: [c_18,
    c_19, c_20], c_12: [c_21, c_22, c_4]}
report = grade_students(students)
display_report(report)


