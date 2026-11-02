"""EDA agent with full-dataset Python/SQL analysis and recorded evidence."""
from llm_support import message_text
import json

import numpy as np
import pandas as pd
from eda_execution import execute_python, execute_sql, PYTHON_MEMORY, PYTHON_TIMEOUT


def _clean(value):
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, bytes):
        return {'type': 'blob', 'hex': value.hex()}
    if isinstance(value, float) and not np.isfinite(value):
        return None
    if value is pd.NA or value is pd.NaT:
        return None
    return value


def query_dataset(df, target, request):
    """Execute an aggregate, containerized Python, or in-memory SQL request."""
    operation = request.get('operation')
    if operation == 'python':
        return execute_python(df, target, request.get('code'))
    if operation == 'sql':
        return _clean(execute_sql(df, target, request.get('sql')))
    columns = request.get('columns', [])
    if not isinstance(columns, list) or len(columns) > 2:
        raise ValueError('Choose at most two columns.')
    if any(not isinstance(c, str) or c not in df.columns for c in columns):
        raise ValueError('Unknown column.')
    if operation == 'correlations':
        numeric = df.select_dtypes(include=[np.number])
        if target not in numeric:
            return []
        values = numeric.corr(method='spearman')[target].drop(target).dropna()
        names = values.abs().sort_values(ascending=False).head(20).index
        return _clean(values.loc[names].to_dict())
    if operation == 'distribution' and len(columns) == 1:
        series = df[columns[0]]
        result = {'column': columns[0], 'missing': int(series.isna().sum()),
                  'distinct': int(series.nunique())}
        if pd.api.types.is_numeric_dtype(series):
            result['summary'] = series.describe(percentiles=[.05, .25, .5, .75, .95]).to_dict()
        else:
            result['values'] = [{'value': str(k), 'count': int(v)} for k, v in
                                series.dropna().value_counts().head(20).items()]
        return _clean(result)
    if operation == 'group_summary' and columns and target not in columns:
        if any(df[c].nunique() > 30 for c in columns):
            raise ValueError('Group summaries require columns with at most 30 values.')
        grouped = df.groupby(columns, dropna=False, observed=True)[target]
        result = grouped.agg(['count', 'mean', 'median', 'std', 'min', 'max'])
        result = result.sort_values('count', ascending=False).head(20)
        return _clean([
            {'conditions': dict(zip(columns, key if isinstance(key, tuple) else (key,))),
             'statistics': row.to_dict()}
            for key, row in result.iterrows()
        ])
    raise ValueError('Use python, sql, distribution, group_summary, or correlations.')


def run_eda_agent(df, target, baseline, llm, user_intent='', selected_test_type=None,
                  on_progress=None):
    """Create the dataset summary from schema and executed queries.

    Continue querying until a valid synthesis is returned. 
    """
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    context = json.loads(baseline)
    evidence = []
    instructions = '''You are HELIOS's **Exploratory Data Analysis (EDA) agent**. Explore the dataset and extract
what you consider to be the most important features and metrics to guide hypothesis generation. Use the user intent to guide your generation *ALWAYS*. Write all narrative text, including summaries, reports, directions and limitations, in English. The hypothesis generator receives your completed context and query evidence, not the raw dataset. You have access to all rows and columns of the uploaded dataset through Python and SQL, including individual records when needed.
Four statistical tests are available in the Hypothesis generator agent:
-One sample t test
-Welch test
-Levene test
-ANOVA test
Guide the output of your exploration considering this. The hypothesis generator generates hypothesis containing up to 4 columns in the dataset, also consider this when exploring.

The complete dataset is already loaded as the pandas DataFrame df for Python and as the table dataset for SQL. Use Python and/or SQL to inspect the dataset and investigate
the user intent before producing your final output *ALWAYS*. You decide which analyses to run and how many queries are needed.

Return ONLY one JSON object per turn, without markdown.
To execute Python: {"action":"query","operation":"python","code":"result = df.describe(include='all')"}. Python runs in an isolated container with the full pandas DataFrame df, target (target column name), pd (pandas), np (numpy), stats (scipy.stats). You can import installed libraries, including scipy, statsmodels, sklearn and matplotlib, define functions, filter any rows, engineer features and run tests.

To execute SQL: {"action":"query","operation":"sql","sql":"SELECT * FROM dataset LIMIT 5"}. SQL uses SQLite with the full dataset in table dataset. Use CTEs, joins, window functions, filters, aggregates and temporary derived tables. Quote column names with double quotes when needed.

To finish: {"action":"finish","summary":"dataset context for hypothesis generation","execution_report":"what you executed and found","hypothesis_directions":["directions"],"limitations":["limitations"]}.''' + '\n\n## User Intent\n\n' + str(user_intent or '')
    messages = [SystemMessage(content=instructions), HumanMessage(content=json.dumps({
        'target': target, 'selected_test_type': selected_test_type,
        'user_intent': user_intent,
    }, ensure_ascii=False))]
    turn = 0
    while True:
        turn += 1
        if on_progress:
            on_progress(f'EDA agent: exploring dataset (step {turn})...')
        response = llm.invoke(messages)
        content = message_text(response)
        content = str(content).strip()
        if content.startswith('```'):
            content = content.split('\n', 1)[-1].rsplit('```', 1)[0].strip()
        try:
            action = json.loads(content)
            if not isinstance(action, dict):
                raise ValueError('Return a JSON object.')
            if action.get('action') == 'finish':
                if not any(item['query'].get('operation') in ('python', 'sql')
                           and not (isinstance(item['result'], dict) and item['result'].get('error'))
                           for item in evidence):
                    raise ValueError('Before finishing, execute a successful Python or SQL query '
                                     'against the dataset to investigate the user intent. '
                                     'A proposed analysis or a failed query is not executed evidence.')
                summary = action.get('summary')
                directions = action.get('hypothesis_directions', [])
                limitations = action.get('limitations', [])
                if not isinstance(summary, str) or not summary.strip():
                    raise ValueError('Return a nonempty summary.')
                if any(not isinstance(items, list) or any(not isinstance(x, str) for x in items)
                       for items in (directions, limitations)):
                    raise ValueError('Directions and limitations must be lists of strings.')
                context['eda_agent'] = {'status': 'completed', 'summary': summary,
                    'hypothesis_directions': directions, 'limitations': limitations,
                    'evidence': evidence,
                    'execution_report': action.get('execution_report') or summary,
                    'data_access': {'backend_rows': len(df), 'available_columns': list(df.columns),
                        'model_access': 'Full dataset available through Python and SQL; profile, aggregates and selected raw rows can be returned to the model.',
                        'python_environment': f'Docker container, no network or host mounts, {PYTHON_TIMEOUT} seconds, {PYTHON_MEMORY} memory',
                        'sql_environment': 'Fresh in-memory SQLite database per call, 20 seconds',
                        'code_execution_operations': [item['query']['operation'] for item in evidence
                            if item['query'].get('operation') in ('python', 'sql')],
                        'columns_accessible_to_code': list(df.columns),
                        'code_column_access_note': 'Python/SQL can access every column; exact accessed columns are not inferred from arbitrary code.',
                        'queried_columns': sorted(set(c for item in evidence for c in
                            (list(df.select_dtypes(include=[np.number]).columns) if item['query'].get('operation') == 'correlations'
                             else item['query'].get('columns', [])))),
                        'target': target},
                    'query_count': len(evidence)}
                return json.dumps(context, ensure_ascii=False, allow_nan=False)
            if action.get('action') != 'query':
                raise ValueError('Choose action query or finish.')
        except (ValueError, TypeError) as exc:
            has_executed_evidence = any(item['query'].get('operation') in ('python', 'sql')
                and not (isinstance(item['result'], dict) and item['result'].get('error'))
                for item in evidence)
            next_step = ('Use the recorded query results to continue exploring or finish with an evidence-based report.'
                         if has_executed_evidence else
                         'Return a Python or SQL query action to inspect the actual dataset. '
                         'Do not finish using only user intent or assumed dataset information. '
                         'If execution failed, correct the query or try the other tool.')
            messages.extend([AIMessage(content=content), HumanMessage(content=
                f'Invalid response: {exc} Correct the response using the requested JSON schema. '
                + next_step)])
            continue
        try:
            if on_progress:
                on_progress(f"EDA agent: executing {action.get('operation')} (step {turn})...")
            result = query_dataset(df, target, action)
        except Exception as exc:
            result = {'error': str(exc)}
        evidence.append({'query': action, 'result': result})
        messages.extend([AIMessage(content=content), HumanMessage(content=json.dumps(
            {'query_result': result}, ensure_ascii=False, allow_nan=False))])
