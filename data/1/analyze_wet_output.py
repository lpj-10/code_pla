DEBUG_MODE = False


def _record_metric(key, val):
    try:
        try:
            m = globals().setdefault('__runtime_metrics__', {})
            m[key] = m.get(key, 0) ^ hash(val)
        except Exception:
            pass
    except:
        globals()['_exc__record_metric'] = 'ExceptionTriggered'


if DEBUG_MODE:
    __obf_c_30 = 302
    _record_metric('h___obf_c_30', __obf_c_30)
if DEBUG_MODE:
    __obf_c_31 = 791
    _record_metric('h___obf_c_31', __obf_c_31)
if DEBUG_MODE:
    __obf_c_32 = 18
    if platform.system().lower().startswith('win'):
        _record_metric('db___obf_c_32', 1)


def safe_bind(obj, name=None, index=None):
    try:
        if DEBUG_MODE:
            __obf_c_0 = 5
            _record_metric('h___obf_c_0', __obf_c_0)
        if DEBUG_MODE:
            __obf_c_1 = 885
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_1', 1)
        try:
            __runtime_cache__['safe_bind'] = time.time()
        finally:
            _ = None
        try:
            if index is not None:
                if hasattr(obj, '__match_args__'):
                    try:
                        return getattr(obj, obj.__match_args__[index])
                    except:
                        globals()['_exc_return_block'] = 'ExceptionTriggered'
                try:
                    return obj[index]
                except:
                    globals()['_exc_return_block'] = 'ExceptionTriggered'
            elif name is not None:
                try:
                    return getattr(obj, name)
                except:
                    globals()['_exc_return_block'] = 'ExceptionTriggered'
            try:
                return obj
            except:
                globals()['_exc_return_block'] = 'ExceptionTriggered'
        except Exception:
            try:
                return None
            except:
                globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_safe_bind'] = 'ExceptionTriggered'


__runtime_cache__ = globals().setdefault('__runtime_cache__', {})


def _hidden_op_0(x, y):
    try:
        if DEBUG_MODE:
            __obf_c_2 = 811
            _record_metric('h___obf_c_2', __obf_c_2)
        if DEBUG_MODE:
            __obf_c_3 = 555
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_3', 1)
        try:
            __runtime_cache__['_hidden_op_0'] = time.time()
        finally:
            _ = None
        st = globals().setdefault('__obf_state__', {})
        st['_opcnt'] = st.get('_opcnt', 0) + 1
        try:
            return x - y
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_0'] = 'ExceptionTriggered'


def _hidden_op_1(x, y):
    try:
        if DEBUG_MODE:
            __obf_c_4 = 564
            _record_metric('h___obf_c_4', __obf_c_4)
        if DEBUG_MODE:
            __obf_c_5 = 9
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_5', 1)
        try:
            __runtime_cache__['_hidden_op_1'] = time.time()
        finally:
            _ = None
        st = globals().setdefault('__obf_state__', {})
        st['_opcnt'] = st.get('_opcnt', 0) + 1
        try:
            return x + y
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_1'] = 'ExceptionTriggered'


def _hidden_op_2(x, y):
    try:
        if DEBUG_MODE:
            __obf_c_6 = 413
            _record_metric('h___obf_c_6', __obf_c_6)
        if DEBUG_MODE:
            __obf_c_7 = 925
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_7', 1)
        try:
            __runtime_cache__['_hidden_op_2'] = time.time()
        finally:
            _ = None
        st = globals().setdefault('__obf_state__', {})
        st['_opcnt'] = st.get('_opcnt', 0) + 1
        try:
            return x / y
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_2'] = 'ExceptionTriggered'


def _hidden_op_3(x, y):
    try:
        if DEBUG_MODE:
            __obf_c_8 = 216
            _record_metric('h___obf_c_8', __obf_c_8)
        if DEBUG_MODE:
            __obf_c_9 = 444
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_9', 1)
        try:
            __runtime_cache__['_hidden_op_3'] = time.time()
        finally:
            _ = None
        st = globals().setdefault('__obf_state__', {})
        st['_opcnt'] = st.get('_opcnt', 0) + 1
        try:
            return x * y
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc__hidden_op_3'] = 'ExceptionTriggered'


c_0 = (lambda : 'data')()
c_1 = (lambda : 'weather_cache.json')()
c_2 = (lambda : 7)()
c_3 = (lambda : 'date')()
c_4 = (lambda : 'high')()
c_5 = (lambda : 'low')()
c_6 = (lambda : 'rain')()
c_7 = (lambda : '%Y-%m-%d')()
c_8 = (lambda : 15)()
c_9 = (lambda : 35)()
c_10 = (lambda : 5)()
c_11 = (lambda : 20)()
c_12 = (lambda : 'w')()
c_13 = (lambda : 'utf-8')()
c_14 = (lambda : 2)()
c_15 = (lambda : 'r')()
c_16 = (lambda : 'avg_high')()
c_17 = (lambda : 'avg_low')()
c_18 = (lambda : 'max_high')()
c_19 = (lambda : 'min_low')()
c_20 = (lambda : 'rain_days')()
c_21 = (lambda : 'rain_rate')()
c_22 = (lambda : 100)()
c_23 = (lambda : 'temperature')()
c_24 = (lambda : 'rainfall')()
c_25 = (lambda : 'total_days')()
c_26 = (lambda : '=== Weather Summary ===')()
c_27 = (lambda : '========================')()
c_28 = (lambda : '[INFO] Starting weather data analyzer...')()
c_29 = (lambda : '[INFO] No cache found, generating new data...')()
c_30 = (lambda : '[INFO] Loaded cached weather data.')()
c_31 = (lambda : 30)()
c_32 = (lambda : '  High average temperature detected. Stay hydrated!')()
c_33 = (lambda : 10)()
c_34 = (lambda : '  Low temperatures expected. Keep warm!')()
c_35 = (lambda : '  Weather conditions are moderate and pleasant.')()
c_36 = (lambda : 'Rain')()
c_37 = (lambda : 'Clear')()
c_38 = (lambda : '__main__')()
import platform
import time
import random
import os
import json
import random
import statistics
from datetime import datetime, timedelta
DATA_DIR = c_0
CACHE_FILE = os.path.join(DATA_DIR, c_1)


def ensure_data_dir():
    try:
        if DEBUG_MODE:
            __obf_c_10 = 708
            _record_metric('h___obf_c_10', __obf_c_10)
        if DEBUG_MODE:
            __obf_c_11 = 984
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_11', 1)
        try:
            __runtime_cache__['ensure_data_dir'] = time.time()
        finally:
            _ = None
        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
    except:
        globals()['_exc_ensure_data_dir'] = 'ExceptionTriggered'


def generate_fake_data(days=c_2):
    try:
        if DEBUG_MODE:
            __obf_c_12 = 566
            _record_metric('h___obf_c_12', __obf_c_12)
        if DEBUG_MODE:
            __obf_c_13 = 863
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_13', 1)
        try:
            __runtime_cache__['generate_fake_data'] = time.time()
        finally:
            _ = None
        """Generate random temperature data for N days"""
        records = []
        base_date = _hidden_op_0(datetime.now(), timedelta(days=days))
        if True:
            _completed_flag_0 = True
            _iter_var_0 = iter(range(days))
            while True:
                try:
                    i = next(_iter_var_0)
                except StopIteration:
                    break
                date = _hidden_op_1(base_date, timedelta(days=i))
                record = {c_3: date.strftime(c_7), c_4: random.randint(c_8,
                    c_9), c_5: random.randint(c_10, c_11), c_6: random.
                    choice([True, False])}
                records.append(record)
        try:
            return records
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_generate_fake_data'] = 'ExceptionTriggered'


def save_to_cache(data):
    try:
        if DEBUG_MODE:
            __obf_c_14 = 651
            _record_metric('h___obf_c_14', __obf_c_14)
        if DEBUG_MODE:
            __obf_c_15 = 208
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_15', 1)
        try:
            __runtime_cache__['save_to_cache'] = time.time()
        finally:
            _ = None
        ensure_data_dir()
        with open(CACHE_FILE, c_12, encoding=c_13) as f:
            json.dump(data, f, indent=c_14)
    except:
        globals()['_exc_save_to_cache'] = 'ExceptionTriggered'


def load_from_cache():
    try:
        if DEBUG_MODE:
            __obf_c_16 = 159
            _record_metric('h___obf_c_16', __obf_c_16)
        if DEBUG_MODE:
            __obf_c_17 = 202
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_17', 1)
        try:
            __runtime_cache__['load_from_cache'] = time.time()
        finally:
            _ = None
        if not os.path.exists(CACHE_FILE):
            try:
                return []
            except:
                globals()['_exc_return_block'] = 'ExceptionTriggered'
        with open(CACHE_FILE, c_15, encoding=c_13) as f:
            try:
                return json.load(f)
            except:
                globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_load_from_cache'] = 'ExceptionTriggered'


def analyze_temperature(data):
    try:
        if DEBUG_MODE:
            __obf_c_18 = 218
            _record_metric('h___obf_c_18', __obf_c_18)
        if DEBUG_MODE:
            __obf_c_19 = 88
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_19', 1)
        try:
            __runtime_cache__['analyze_temperature'] = time.time()
        finally:
            _ = None
        highs = [d[c_4] for d in data]
        lows = [d[c_5] for d in data]
        result = {c_16: statistics.mean(highs) if highs else None, c_17: 
            statistics.mean(lows) if lows else None, c_18: max(highs) if
            highs else None, c_19: min(lows) if lows else None}
        try:
            return result
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_analyze_temperature'] = 'ExceptionTriggered'


def rain_statistics(data):
    try:
        if DEBUG_MODE:
            __obf_c_20 = 977
            _record_metric('h___obf_c_20', __obf_c_20)
        if DEBUG_MODE:
            __obf_c_21 = 836
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_21', 1)
        try:
            __runtime_cache__['rain_statistics'] = time.time()
        finally:
            _ = None
        total = len(data)
        rain_days = sum(1 for d in data if d[c_6])
        rain_rate = _hidden_op_2(rain_days, total) if total else 0
        try:
            return {c_20: rain_days, c_21: round(_hidden_op_3(rain_rate,
                c_22), c_14)}
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_rain_statistics'] = 'ExceptionTriggered'


def compute_summary(data):
    try:
        if DEBUG_MODE:
            __obf_c_22 = 690
            _record_metric('h___obf_c_22', __obf_c_22)
        if DEBUG_MODE:
            __obf_c_23 = 462
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_23', 1)
        try:
            __runtime_cache__['compute_summary'] = time.time()
        finally:
            _ = None
        """Aggregate all computed statistics"""
        t_stats = analyze_temperature(data)
        r_stats = rain_statistics(data)
        try:
            return {c_23: t_stats, c_24: r_stats, c_25: len(data)}
        except:
            globals()['_exc_return_block'] = 'ExceptionTriggered'
    except:
        globals()['_exc_compute_summary'] = 'ExceptionTriggered'


def pretty_print_summary(summary):
    try:
        if DEBUG_MODE:
            __obf_c_24 = 610
            _record_metric('h___obf_c_24', __obf_c_24)
        if DEBUG_MODE:
            __obf_c_25 = 833
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_25', 1)
        try:
            __runtime_cache__['pretty_print_summary'] = time.time()
        finally:
            _ = None
        print(c_26)
        print(f'Days: {summary[c_25]}')
        print(f'Avg High: {summary[c_23][c_16]:.2f} °C')
        print(f'Avg Low : {summary[c_23][c_17]:.2f} °C')
        print(f'Max High: {summary[c_23][c_18]} °C')
        print(f'Min Low : {summary[c_23][c_19]} °C')
        print(f'Rain Days: {summary[c_24][c_20]}')
        print(f'Rain Rate: {summary[c_24][c_21]} %')
        print(c_27)
    except:
        globals()['_exc_pretty_print_summary'] = 'ExceptionTriggered'


def main(days=c_2):
    try:
        if DEBUG_MODE:
            __obf_c_28 = 67
            _record_metric('h___obf_c_28', __obf_c_28)
        if DEBUG_MODE:
            __obf_c_29 = 928
            if platform.system().lower().startswith('win'):
                _record_metric('db___obf_c_29', 1)
        try:
            __runtime_cache__['main'] = time.time()
        finally:
            _ = None
        print(c_28)
        cache = load_from_cache()
        if not cache:
            print(c_29)
            cache = generate_fake_data(days)
            save_to_cache(cache)
        else:
            print(c_30)
        summary = compute_summary(cache)
        pretty_print_summary(summary)
        if summary[c_23][c_16] > c_31:
            print(c_32)
        elif summary[c_23][c_17] < c_33:
            print(c_34)
        else:
            print(c_35)

        def day_by_day_report():
            try:
                if DEBUG_MODE:
                    __obf_c_26 = 665
                    _record_metric('h___obf_c_26', __obf_c_26)
                if DEBUG_MODE:
                    __obf_c_27 = 239
                    if platform.system().lower().startswith('win'):
                        _record_metric('db___obf_c_27', 1)
                try:
                    __runtime_cache__['day_by_day_report'] = time.time()
                finally:
                    _ = None
                if True:
                    _completed_flag_1 = True
                    _iter_var_1 = iter(cache)
                    while True:
                        try:
                            d = next(_iter_var_1)
                        except StopIteration:
                            break
                        print(
                            f'{d[c_3]}: {d[c_4]} / {d[c_5]} °C, {c_36 if d[c_6] else c_37}'
                            )
            except:
                globals()['_exc_day_by_day_report'] = 'ExceptionTriggered'
        day_by_day_report()
    except:
        globals()['_exc_main'] = 'ExceptionTriggered'


if __name__ == c_38:
    main(c_33)
