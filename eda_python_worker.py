"""Python analysis worker. Production execution is inside the EDA Docker image."""
import ast
import contextlib
import io
import json
import math
import sys
import traceback
import numpy as np
import pandas as pd
from scipy import stats


class LimitedOutput(io.StringIO):
    def write(self, text):
        remaining = max(0, 20000 - self.tell())
        super().write(text[:remaining])
        return len(text)


def encode(value, depth=0):
    if depth > 12:
        return '<maximum nesting reached>'
    if isinstance(value, pd.DataFrame):
        return {'type': 'dataframe', 'shape': list(value.shape),
                'columns': [str(c) for c in value.columns[:100]],
                'rows': encode(value.iloc[:100, :100].astype(object).values.tolist(), depth + 1),
                'truncated': value.shape[0] > 100 or value.shape[1] > 100}
    if isinstance(value, pd.Series):
        return {'type': 'series', 'size': len(value), 'name': str(value.name),
                'index': encode(value.index[:100].tolist(), depth + 1),
                'values': encode(value.iloc[:100].tolist(), depth + 1), 'truncated': len(value) > 100}
    if isinstance(value, np.ndarray):
        return {'type': 'array', 'shape': list(value.shape),
                'values': encode(value.reshape(-1)[:100].tolist(), depth + 1), 'truncated': value.size > 100}
    if isinstance(value, dict):
        output = {str(k): encode(v, depth + 1) for k, v in list(value.items())[:100]}
        if len(value) > 100:
            output['__truncated__'] = True
        return output
    if isinstance(value, (list, tuple, set)):
        items = list(value)
        output = [encode(v, depth + 1) for v in items[:100]]
        if len(items) > 100:
            output.append({'__truncated__': True, 'total_items': len(items)})
        return output
    if isinstance(value, np.generic):
        return encode(value.item(), depth + 1)
    if value is pd.NA or value is pd.NaT:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value[:20000] if isinstance(value, str) else value
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)[:20000]


def main():
    request = json.load(sys.stdin)
    df = pd.read_json(io.StringIO(request['dataframe']), orient='table')
    output = LimitedOutput()
    namespace = {'df': df, 'target': request['target'], 'pd': pd, 'np': np,
                 'stats': stats, 'result': None, '__name__': '__eda_analysis__'}
    try:
        tree = ast.parse(request['code'], mode='exec')
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            expression = tree.body[-1]
            tree.body[-1] = ast.copy_location(ast.Assign(
                targets=[ast.Name(id='result', ctx=ast.Store())], value=expression.value), expression)
            ast.fix_missing_locations(tree)
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            exec(compile(tree, '<eda-python>', 'exec'), namespace)
        response = {'result': encode(namespace.get('result')), 'stdout': output.getvalue(),
                    'dataset_shape': list(df.shape), 'output_limit_rows': 100}
    except BaseException as exc:
        response = {'error': f'{type(exc).__name__}: {exc}', 'stdout': output.getvalue(),
                    'traceback': traceback.format_exc()[-8000:]}
    # Serialize after execution; cap even deeply expanded compound results.
    payload = json.dumps(response, ensure_ascii=False, allow_nan=False)
    if len(payload) > 100000:
        payload = json.dumps({'error': 'Result exceeds 100000 characters. Return a smaller result.',
                              'stdout': output.getvalue()})
    sys.stdout.write(payload)


if __name__ == '__main__':
    main()
