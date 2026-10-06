# [NEW v17] Probe native acceleration outside the application process.
import os
import subprocess
import sys
import warnings

STATUS = {'backend': 'python', 'reason': 'not probed'}

def python_njit(*args, **kwargs):
    if args and callable(args[0]):
        return args[0]
    return lambda fn: fn

def probe_numba(executable=None):
    if os.environ.get('CFRP_DISABLE_NUMBA') == '1':
        return {'backend': 'python', 'reason': 'CFRP_DISABLE_NUMBA=1'}
    code = 'import numba, llvmlite; f=numba.njit(lambda x:x+1); assert f(1)==2; print(numba.__version__,llvmlite.__version__)'
    try:
        result = subprocess.run([executable or sys.executable, '-c', code], capture_output=True, text=True, timeout=45)
        if result.returncode != 0:
            return {'backend': 'python', 'reason': 'native probe exit=' + str(result.returncode), 'detail': result.stderr[-2000:]}
        return {'backend': 'numba', 'reason': 'isolated import/JIT probe passed', 'versions': result.stdout.strip()}
    except (OSError, subprocess.TimeoutExpired) as error:
        return {'backend': 'python', 'reason': str(error)}

def select_njit():
    STATUS.update(probe_numba())
    if STATUS['backend'] == 'numba':
        try:
            from numba import njit
            return njit
        except Exception as error:
            STATUS.update(backend='python', reason=str(error))
    warnings.warn('CFRP uses Python solver: ' + STATUS['reason'] + '; calculation may be slower.', RuntimeWarning)
    return python_njit

safe_njit = select_njit()
