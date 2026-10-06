# [NEW v18] Python 3.14 Windows installation profile.
# [NEW v17] Windows-only bootstrap; no runtime dependency before installation.
import hashlib
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def logged_run(command=None, log_path=None, env=None):
    with Path(log_path).open('w', encoding='utf-8') as log:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        for line in process.stdout:
            print(line, end='', flush=True)
            log.write(line)
        return process.wait()

def main():
    if os.name != 'nt':
        print('This distribution launcher supports Windows only.')
        return 1
    if sys.version_info[:2] != (3, 14):
        print('Python 3.14 is required. Use py -3.14 windows_launcher_v17.py.')
        return 1
    # [NEW v18] Use normal 64-bit CPython, with published cp314 wheels.
    import struct
    import sysconfig
    if struct.calcsize('P') != 8 or sysconfig.get_config_var('Py_GIL_DISABLED'):
        print('Use standard 64-bit CPython 3.14, not 32-bit or free-threaded 3.14t.')
        return 1
    env = dict(os.environ, PYTHONUTF8='1', PYTHONUNBUFFERED='1')
    folder = ROOT / '.venv_windows_py314_v18'
    python = folder / 'Scripts/python.exe'
    marker = folder / 'ready_v18.txt'
    requirements = ROOT / 'requirements-windows-py314-v18.txt'
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    if not python.is_file():
        result = logged_run([sys.executable, '-m', 'venv', str(folder)], ROOT/'setup_windows_v18.log', env)
        if result != 0:
            return result
    if not marker.is_file() or marker.read_text(encoding='utf-8') != fingerprint:
        result = logged_run([str(python), '-m', 'pip', 'install', '--only-binary=:all:', '-r', str(requirements)], ROOT/'setup_windows_v18.log', env)
        if result != 0:
            print('Installation failed. See setup_windows_v18.log.')
            return result
    result = logged_run([str(python), 'check_html_runtime_v15.py'], ROOT/'runtime_check_v18.log', env)
    if result != 0:
        marker.unlink(missing_ok=True)
        print('Runtime check failed. See runtime_check_v18.log.')
        return result
    marker.write_text(fingerprint, encoding='utf-8')
    print('Starting http://127.0.0.1:8765/ ; keep this console open.')
    return subprocess.call([str(python), 'interactive_server.py'], cwd=ROOT, env=env)

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print('Windows startup failed:', error)
        raise SystemExit(1)
