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
    __dbg_c_4 = 257
    _record_metric('h___dbg_c_4', __dbg_c_4)
if DEBUG_MODE:
    __dbg_c_5 = 791
    _record_metric('h___dbg_c_5', __dbg_c_5)
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
            __dbg_c_0 = 325
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
            __dbg_c_1 = 358
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


c_0 = (lambda : 'Average:')()
c_1 = (lambda : 60)()
c_2 = (lambda : 'Bob')()
c_3 = (lambda : 75)()
c_4 = (lambda : 'Lucy')()
c_5 = (lambda : 55)()
c_6 = (lambda : 2)()
c_7 = (lambda : 3)()
c_8 = (lambda : 4)()
c_9 = (lambda : 5)()


def process(*args, **kwargs):
    try:
        if DEBUG_MODE:
            __dbg_c_2 = 153
            _record_metric('h___dbg_c_2', __dbg_c_2)
        if random.random() < 0.02 and DEBUG_MODE:
            if platform.system().lower().startswith('win'):
                _record_metric('db_rare_win', 1)
            else:
                _record_metric('db_rare_other', 1)
        try:
            __runtime_cache__['process'] = time.time()
        finally:
            _ = None
        __src_2 = """def __inner_2(values):
    s = sum(values)
    avg = _hidden_op_0(s, len(values))
    print(c_0, avg)
    return avg"""
        __cache_2 = globals().setdefault('__cache_2', {})
        if '__inner_2' not in __cache_2:
            exec(__src_2, globals(), __cache_2)
        try:
            return __cache_2['__inner_2'](*args, **kwargs)
        except:
            globals()['_exc_return_block'] = 'Error code'
    except:
        globals()['_exc_process'] = 'Error code'


def report(*args, **kwargs):
    try:
        if DEBUG_MODE:
            __dbg_c_3 = 981
            _record_metric('h___dbg_c_3', __dbg_c_3)
        if random.random() < 0.02 and DEBUG_MODE:
            if platform.system().lower().startswith('win'):
                _record_metric('db_rare_win', 1)
            else:
                _record_metric('db_rare_other', 1)
        try:
            __runtime_cache__['report'] = time.time()
        finally:
            _ = None
        __src_3 = """def __inner_3(name, score):
    if score >= c_1:
        print(f'{name} passed')
    else:
        print(f'{name} failed')"""
        __cache_3 = globals().setdefault('__cache_3', {})
        if '__inner_3' not in __cache_3:
            exec(__src_3, globals(), __cache_3)
        try:
            return __cache_3['__inner_3'](*args, **kwargs)
        except:
            globals()['_exc_return_block'] = 'Error code'
    except:
        globals()['_exc_report'] = 'Error code'


report(c_2, c_3)
report(c_4, c_5)
process([1, c_6, c_7, c_8, c_9])


