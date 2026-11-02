"""Full-dataset analysis tools: containerized Python and in-memory SQLite."""
import json
import os
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid

PYTHON_IMAGE = 'helios-eda-python:1'
PYTHON_MEMORY = os.getenv('HELIOS_EDA_PYTHON_MEMORY', '4g')
PYTHON_TIMEOUT = int(os.getenv('HELIOS_EDA_PYTHON_TIMEOUT', '120'))


def execute_sql(df, target, sql, timeout=20, max_rows=100):
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 50000:
        raise ValueError('SQL must be nonempty text of at most 50000 characters.')
    started = time.monotonic()
    connection = sqlite3.connect(':memory:')
    try:
        df.to_sql('dataset', connection, index=False, if_exists='replace')
        # All dataset statements are permitted; external databases and extension
        # loading are outside the dataset-only execution scope.
        connection.enable_load_extension(False)
        def authorize(action, arg1, arg2, database, source):
            if action in (sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH):
                return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_FUNCTION and (arg2 or '').lower() == 'load_extension':
                return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_PRAGMA and (arg1 or '').lower() not in ('table_info', 'table_xinfo'):
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        connection.set_authorizer(authorize)
        connection.set_progress_handler(lambda: int(time.monotonic() - started > timeout), 1000)
        statements, pending = [], ''
        for char in sql:
            pending += char
            if char == ';' and sqlite3.complete_statement(pending):
                statements.append(pending)
                pending = ''
        if pending.strip():
            statements.append(pending)
        result = {'columns': [], 'rows': [], 'truncated': False}
        for statement in statements:
            cursor = connection.execute(statement)
            if cursor.description:
                rows = cursor.fetchmany(max_rows + 1)
                result = {'columns': [c[0] for c in cursor.description],
                          'rows': [list(row) for row in rows[:max_rows]], 'truncated': len(rows) > max_rows}
        result.update({'engine': 'SQLite', 'statements': len(statements),
                       'elapsed_seconds': round(time.monotonic() - started, 3), 'output_limit_rows': max_rows})
        return result
    finally:
        connection.close()


def _run_container(command, payload, name, timeout):
    """Bound both pipe streams while enforcing a container wall-clock limit."""
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, creationflags=creationflags)
    streams, overflow = {'stdout': bytearray(), 'stderr': bytearray()}, threading.Event()
    def read(pipe, key):
        while True:
            chunk = pipe.read(4096)
            if not chunk:
                break
            if len(streams[key]) + len(chunk) > 128000:
                overflow.set()
                break
            streams[key].extend(chunk)
        pipe.close()
    def write():
        try:
            process.stdin.write(payload)
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass
    threads = [threading.Thread(target=read, args=(process.stdout, 'stdout'), daemon=True),
               threading.Thread(target=read, args=(process.stderr, 'stderr'), daemon=True),
               threading.Thread(target=write, daemon=True)]
    for thread in threads:
        thread.start()
    deadline = time.monotonic() + timeout
    stopped = None
    while process.poll() is None:
        if overflow.is_set() or time.monotonic() >= deadline:
            stopped = 'Python output limit exceeded.' if overflow.is_set() else f'Python execution exceeded {timeout} seconds.'
            # Killing the Docker client alone does not stop its container.
            try:
                subprocess.run([command[0], 'rm', '-f', name], capture_output=True,
                               timeout=10, creationflags=creationflags)
            finally:
                process.kill()
            break
        time.sleep(.02)
    process.wait(timeout=10)
    for thread in threads:
        thread.join(timeout=2)
    if stopped or overflow.is_set():
        raise RuntimeError(stopped or 'Python output limit exceeded.')
    return process.returncode, streams['stdout'].decode('utf-8', errors='replace'), streams['stderr'].decode('utf-8', errors='replace')


def execute_python(df, target, code, timeout=None):
    timeout = PYTHON_TIMEOUT if timeout is None else timeout
    if not isinstance(code, str) or not code.strip() or len(code) > 50000:
        raise ValueError('Python code must be nonempty text of at most 50000 characters.')
    docker = shutil.which('docker')
    if not docker:
        raise RuntimeError('Docker is required for Python execution. Start Docker Desktop and run setup_eda_python.ps1.')
    name = 'helios-eda-' + uuid.uuid4().hex
    command = [docker, 'run', '--rm', '-i', '--pull=never', '--name', name,
               '--network=none', '--read-only', '--cap-drop=ALL',
               '--security-opt=no-new-privileges', '--memory=' + PYTHON_MEMORY, '--memory-swap=' + PYTHON_MEMORY,
               '--cpus=1', '--pids-limit=64', '--user=65534:65534',
               '--tmpfs=/tmp:rw,nosuid,noexec,size=128m', PYTHON_IMAGE]
    payload = json.dumps({'dataframe': df.to_json(orient='table'), 'target': target, 'code': code}).encode('utf-8')
    status, stdout, stderr = _run_container(command, payload, name, timeout)
    if status:
        if status == 137:
            raise RuntimeError('Python container was terminated (exit 137), commonly due to insufficient memory. '
                               'Current limit: ' + PYTHON_MEMORY + '. Increase HELIOS_EDA_PYTHON_MEMORY if needed. '
                               'Details: ' + stderr[-4000:])
        raise RuntimeError(f'Python container failed (exit {status}). Check Docker Desktop and the EDA image. Details: ' + stderr[-4000:])
    try:
        return json.loads(stdout)
    except ValueError as exc:
        raise RuntimeError('Python worker did not return valid JSON: ' + stdout[-2000:]) from exc
