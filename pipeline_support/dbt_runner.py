"""Run the existing dbt build with live Mage logs and private run artifacts."""
from collections import Counter, deque
import json
import os
from pathlib import Path
import signal
import subprocess
import threading
import uuid


def stop_process(process):
    if process.poll() is not None:
        return
    try:
        if os.name == 'posix':
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            if os.name == 'posix':
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except ProcessLookupError:
            return
        process.wait(timeout=10)


def build_dbt(project_root, environment, *, executable=None, timeout_seconds=3600,
              progress=print):
    if isinstance(timeout_seconds, bool) or int(timeout_seconds) != float(timeout_seconds):
        raise ValueError('dbt_timeout_seconds must be a positive integer')
    timeout_seconds = int(timeout_seconds)
    if timeout_seconds <= 0:
        raise ValueError('dbt_timeout_seconds must be a positive integer')
    root = Path(project_root).resolve()
    project = root / 'dbt_transform'
    if not (project / 'dbt_project.yml').is_file():
        raise ValueError('Cannot find the existing dbt_transform project')
    executable = executable or os.environ.get('DBT_EXECUTABLE', '/opt/dbt-venv/bin/dbt')
    artifacts = root / 'output' / 'dbt_runs' / uuid.uuid4().hex
    artifacts.mkdir(parents=True)
    env = os.environ.copy()
    env.update(environment)
    env.update(DBT_TARGET_PATH=str(artifacts / 'target'),
               DBT_LOG_PATH=str(artifacts / 'logs'),
               DBT_PROFILES_DIR=str(project), DBT_SEND_ANONYMOUS_USAGE_STATS='false',
               DBT_USE_COLORS='false', DBT_PARTIAL_PARSE='false')
    for key in ('DBT_SELECT', 'DBT_EXCLUDE', 'DBT_FULL_REFRESH'):
        env.pop(key, None)
    command = [str(executable), 'build', '--project-dir', str(project),
               '--profiles-dir', str(project), '--target', 'dev', '--threads', '1']
    tail = deque(maxlen=12)
    password = str(env.get('MSSQL_PASSWORD', ''))

    def stream_output():
        for line in process.stdout:
            line = line.rstrip()
            if password:
                line = line.replace(password, '[REDACTED]')
            tail.append(line)
            progress(line)

    progress('DBT BUILD: transforming staging and running all existing dbt tests...')
    try:
        process = subprocess.Popen(command, cwd=project, env=env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding='utf-8', errors='replace',
                                   start_new_session=(os.name == 'posix'))
    except FileNotFoundError as exc:
        raise RuntimeError('dbt runtime is missing. Rebuild Mage with '
                           'docker compose up -d --build mage') from exc
    reader = threading.Thread(target=stream_output, daemon=True)
    reader.start()
    try:
        try:
            code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            stop_process(process)
            raise RuntimeError(f'dbt build exceeded {timeout_seconds} seconds') from exc
        finally:
            reader.join(timeout=10)
        if code:
            raise RuntimeError(f'dbt build failed (exit {code}). ' + '\n'.join(tail))
    finally:
        stop_process(process)
        process.stdout.close()
    result_path = artifacts / 'target' / 'run_results.json'
    if not result_path.is_file():
        raise RuntimeError('dbt returned without run_results.json; cannot confirm success')
    results = json.loads(result_path.read_text(encoding='utf-8')).get('results', [])
    failures = [r for r in results if r.get('status') not in ('success', 'pass')]
    counts = Counter(r.get('unique_id', '').split('.')[0] for r in results)
    if failures or not counts['model'] or not counts['test']:
        detail = ', '.join(f"{r.get('unique_id')}: {r.get('status')}" for r in failures[:10])
        raise RuntimeError('dbt models/tests did not all pass: ' + (detail or 'empty build/test results'))
    report = dict(status='SUCCESS', models=counts['model'], tests=counts['test'],
                  total=len(results), artifact_dir=str(artifacts),
                  run_results_path=str(result_path))
    progress(f"DBT SUCCESS: {report['models']} models; {report['tests']} tests passed")
    return report
