"""Metadata-driven validation rules and KPI configuration engine."""
from contextlib import contextmanager
import hashlib
import json
import re

import pandas as pd

DEFAULT_VALIDATION_RULES = [
    {
        'rule_code': 'REQUIRE_APPID',
        'rule_name': 'Bắt buộc có AppID',
        'target_column': 'AppID',
        'rule_type': 'REQUIRED',
        'params_json': None,
        'on_fail_action': 'REJECT_ROW',
        'is_active': True,
        'sort_order': 10,
    },
    {
        'rule_code': 'VALID_APPID_NUMERIC',
        'rule_name': 'AppID phải là giá trị số hợp lệ',
        'target_column': 'AppID',
        'rule_type': 'NUMERIC',
        'params_json': '{"allow_null": true}',
        'on_fail_action': 'REJECT_ROW',
        'is_active': True,
        'sort_order': 20,
    },
    {
        'rule_code': 'PRICE_NON_NEGATIVE',
        'rule_name': 'Giá game không âm (chuyển NULL nếu < 0)',
        'target_column': 'Price',
        'rule_type': 'MIN_VALUE',
        'params_json': '{"min": 0}',
        'on_fail_action': 'NULLIFY',
        'is_active': True,
        'sort_order': 30,
    },
    {
        'rule_code': 'DISCOUNT_RANGE',
        'rule_name': 'Phần trăm giảm giá nằm trong [0, 100]',
        'target_column': 'Discount',
        'rule_type': 'RANGE',
        'params_json': '{"min": 0, "max": 100}',
        'on_fail_action': 'NULLIFY',
        'is_active': True,
        'sort_order': 40,
    },
    {
        'rule_code': 'METACRITIC_RANGE',
        'rule_name': 'Điểm Metacritic nằm trong [1, 100]',
        'target_column': 'Metacritic score',
        'rule_type': 'RANGE',
        'params_json': '{"min": 1, "max": 100}',
        'on_fail_action': 'NULLIFY',
        'is_active': True,
        'sort_order': 50,
    },
]

DEFAULT_KPI_DEFINITIONS = {
    'PUBLISHER_AAA_MIN_GAMES': {
        'kpi_code': 'PUBLISHER_AAA_MIN_GAMES',
        'kpi_name': 'Ngưỡng phân tầng nhà phát hành AAA',
        'target_model': 'dim_publisher',
        'formula_mode': 'THRESHOLD',
        'kpi_value': '10',
        'params_json': '{"min_games": 10}',
        'version_no': 1,
    },
    'FREE_GAME_RULE': {
        'kpi_code': 'FREE_GAME_RULE',
        'kpi_name': 'Định nghĩa game miễn phí (is_free)',
        'target_model': 'stg_steam_games_cleaned',
        'formula_mode': 'FORMULA_VARIANT',
        'kpi_value': 'PRICE_EQUALS_ZERO',
        'params_json': '{"max_price": 0, "include_100_discount": false}',
        'version_no': 1,
    },
    'POSITIVE_RATIO_FORMULA': {
        'kpi_code': 'POSITIVE_RATIO_FORMULA',
        'kpi_name': 'Công thức tính tỷ lệ đánh giá tích cực',
        'target_model': 'stg_steam_games_cleaned',
        'formula_mode': 'FORMULA_VARIANT',
        'kpi_value': 'STANDARD',
        'params_json': '{"min_reviews": 1, "alpha": 0}',
        'version_no': 1,
    },
}


@contextmanager
def _open_conn(connect):
    if connect is None:
        yield None
        return
    if callable(connect):
        conn = connect()
        try:
            yield conn
        finally:
            conn.close()
    else:
        yield connect


def _parse_params(raw):
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _resolve_column(df, target_column):
    """Find matching column name in df for raw CSV or normalized SQL column names."""
    if target_column in df.columns:
        return target_column
    norm_target = target_column.strip().lower().replace(' ', '_')
    mapping = {c.strip().lower().replace(' ', '_'): c for c in df.columns}
    return mapping.get(norm_target)


def load_validation_rules(connect=None):
    """Load all validation rules from dbo.etl_validation_rules, or defaults offline."""
    with _open_conn(connect) as conn:
        if conn is None:
            return [dict(r) for r in DEFAULT_VALIDATION_RULES]
        try:
            has_table = conn.execute("SELECT OBJECT_ID('dbo.etl_validation_rules', 'U')").fetchone()[0]
            if not has_table:
                return [dict(r) for r in DEFAULT_VALIDATION_RULES]
            rows = conn.execute("""
                SELECT rule_code, rule_name, target_column, rule_type,
                       params_json, on_fail_action, is_active, sort_order
                FROM dbo.etl_validation_rules
                ORDER BY sort_order, rule_id
            """).fetchall()
            if not rows:
                return [dict(r) for r in DEFAULT_VALIDATION_RULES]
            return [
                {
                    'rule_code': str(r[0]),
                    'rule_name': str(r[1]),
                    'target_column': str(r[2]),
                    'rule_type': str(r[3]).upper(),
                    'params_json': r[4],
                    'on_fail_action': str(r[5]).upper(),
                    'is_active': bool(r[6]),
                    'sort_order': int(r[7]),
                }
                for r in rows
            ]
        except Exception:
            return [dict(r) for r in DEFAULT_VALIDATION_RULES]


def load_kpi_definitions(connect=None):
    """Load active KPI definitions from dbo.etl_kpi_definitions, or defaults offline."""
    defaults = {k: dict(v) for k, v in DEFAULT_KPI_DEFINITIONS.items()}
    with _open_conn(connect) as conn:
        if conn is None:
            return defaults
        try:
            has_table = conn.execute("SELECT OBJECT_ID('dbo.etl_kpi_definitions', 'U')").fetchone()[0]
            if not has_table:
                return defaults
            rows = conn.execute("""
                SELECT kpi_code, kpi_name, target_model, formula_mode,
                       kpi_value, params_json, version_no
                FROM dbo.etl_kpi_definitions
            """).fetchall()
            for r in rows:
                defaults[str(r[0])] = {
                    'kpi_code': str(r[0]),
                    'kpi_name': str(r[1]),
                    'target_model': str(r[2]),
                    'formula_mode': str(r[3]),
                    'kpi_value': str(r[4]),
                    'params_json': r[5],
                    'version_no': int(r[6]),
                }
            return defaults
        except Exception:
            return defaults


def _rule_fail_mask(series, rule):
    """Return boolean Series (aligned to series.index) where True means rule failed."""
    rule_type = str(rule.get('rule_type', '')).upper()
    params = _parse_params(rule.get('params_json'))
    is_na = series.isna()

    if rule_type == 'REQUIRED':
        text = series.astype(str).str.strip()
        empty = is_na | (text == '')
        placeholders = [str(p).strip().lower() for p in params.get('disallow_placeholders', [])]
        if placeholders:
            empty = empty | text.str.lower().isin(placeholders)
        return empty

    if rule_type == 'NUMERIC':
        numeric = pd.to_numeric(series, errors='coerce')
        non_empty = ~is_na & (series.astype(str).str.strip() != '')
        failed = non_empty & numeric.isna()
        if not params.get('allow_null', True):
            failed = failed | (~non_empty)
        return failed

    if rule_type == 'MIN_VALUE':
        min_val = float(params.get('min', 0))
        numeric = pd.to_numeric(series, errors='coerce')
        non_empty = ~is_na & (series.astype(str).str.strip() != '')
        failed = numeric.notna() & (numeric < min_val)
        if params.get('numeric'):
            failed = failed | (non_empty & numeric.isna())
        return failed

    if rule_type == 'MAX_VALUE':
        max_val = float(params['max'])
        numeric = pd.to_numeric(series, errors='coerce')
        non_empty = ~is_na & (series.astype(str).str.strip() != '')
        failed = numeric.notna() & (numeric > max_val)
        if params.get('numeric'):
            failed = failed | (non_empty & numeric.isna())
        return failed

    if rule_type == 'RANGE':
        numeric = pd.to_numeric(series, errors='coerce')
        non_empty = ~is_na & (series.astype(str).str.strip() != '')
        failed = pd.Series(False, index=series.index)
        if 'min' in params and params['min'] is not None:
            failed = failed | (numeric.notna() & (numeric < float(params['min'])))
        if 'max' in params and params['max'] is not None:
            failed = failed | (numeric.notna() & (numeric > float(params['max'])))
        if params.get('numeric'):
            failed = failed | (non_empty & numeric.isna())
        return failed

    if rule_type == 'DATE':
        if pd.api.types.is_datetime64_any_dtype(series):
            return series.isna()
        parsed = pd.to_datetime(series.astype(str).str.strip(), errors='coerce')
        return parsed.isna()

    if rule_type == 'REGEX':
        pattern = params.get('pattern', '')
        if not pattern:
            return pd.Series(False, index=series.index)
        compiled = re.compile(pattern)
        non_empty = ~is_na & (series.astype(str).str.strip() != '')
        return non_empty & ~series.astype(str).str.strip().apply(lambda v: bool(compiled.match(v)))

    return pd.Series(False, index=series.index)


def _format_reason_detail(rule, value):
    rule_type = str(rule.get('rule_type', '')).upper()
    params = _parse_params(rule.get('params_json'))
    col = rule.get('target_column', '')
    if rule_type == 'REQUIRED':
        return f'{col} is empty or missing'
    if rule_type == 'DATE':
        return f'{col} is missing or not a valid date'
    if rule_type in ('MIN_VALUE', 'MAX_VALUE', 'RANGE'):
        bounds = ', '.join(f'{k}={params[k]}' for k in ('min', 'max') if k in params and params[k] is not None)
        return f'{col} value {value!r} violated {rule_type} ({bounds})'
    return f'{col} value {value!r} violated rule {rule.get("rule_code")}'


def evaluate_reject_rules(frame, rules, sources=None, chunk_id=None):
    """Evaluate active REJECT_ROW rules against raw frame.

    Returns (rejected_mask_Series, rejection_records_list).
    """
    active_reject = [
        r for r in (rules or DEFAULT_VALIDATION_RULES)
        if r.get('is_active', True) and str(r.get('on_fail_action', '')).upper() == 'REJECT_ROW'
    ]
    rejected_mask = pd.Series(False, index=frame.index)
    records = []

    if frame.empty or not active_reject:
        return rejected_mask, records

    # Evaluate each active REJECT_ROW rule in sort_order
    rule_masks = []
    for rule in active_reject:
        col = _resolve_column(frame, rule['target_column'])
        if col is None:
            continue
        mask = _rule_fail_mask(frame[col], rule)
        rule_masks.append((rule, col, mask))
        rejected_mask = rejected_mask | mask

    if sources is not None:
        # Preserve legacy reason codes for AppID failures when standard rules trigger
        for pos, (idx, record) in enumerate(zip(frame.index, sources, strict=True)):
            matched_rules = [(rule, col) for rule, col, mask in rule_masks if bool(mask.iloc[pos])]
            if not matched_rules:
                continue
            for rule, col in matched_rules:
                code = rule['rule_code']
                if code == 'REQUIRE_APPID':
                    reason_code = 'MISSING_APPID'
                    reason_detail = 'AppID is empty'
                elif code == 'VALID_APPID_NUMERIC':
                    raw_val = str(record.get('raw_appid', '')).strip()
                    reason_code = 'MISSING_APPID' if not raw_val else 'INVALID_APPID'
                    reason_detail = 'AppID is empty' if not raw_val else 'AppID is not numeric or <= 0'
                    # Avoid duplicate entry if REQUIRE_APPID already fired for empty AppID
                    if not raw_val and any(r['rule_code'] == 'REQUIRE_APPID' for r, _ in matched_rules):
                        continue
                else:
                    reason_code = code
                    reason_detail = _format_reason_detail(rule, frame.at[idx, col])
                records.append(dict(
                    record,
                    chunk_id=chunk_id,
                    rejected_stage='VALIDATE',
                    reason_code=reason_code,
                    reason_detail=reason_detail,
                ))

    return rejected_mask, records


def apply_nullify_rules(cleaned_df, rules):
    """Apply active NULLIFY rules to a cleaned DataFrame."""
    if cleaned_df.empty:
        return cleaned_df
    active_nullify = [
        r for r in (rules or [])
        if r.get('is_active', True) and str(r.get('on_fail_action', '')).upper() == 'NULLIFY'
    ]
    if not active_nullify:
        return cleaned_df
    df = cleaned_df.copy()
    for rule in active_nullify:
        col = _resolve_column(df, rule['target_column'])
        if col is None:
            continue
        mask = _rule_fail_mask(df[col], rule)
        if mask.any():
            df.loc[mask, col] = pd.NA
    return df


def build_dbt_vars(rules, kpis):
    """Translate SQL metadata rules & KPI definitions into dbt --vars dict."""
    rule_map = {r['rule_code']: bool(r.get('is_active', True)) for r in (rules or DEFAULT_VALIDATION_RULES)}
    kpi_map = kpis or DEFAULT_KPI_DEFINITIONS

    aaa_def = kpi_map.get('PUBLISHER_AAA_MIN_GAMES', DEFAULT_KPI_DEFINITIONS['PUBLISHER_AAA_MIN_GAMES'])
    aaa_params = _parse_params(aaa_def.get('params_json'))
    try:
        aaa_min_games = int(aaa_params.get('min_games', aaa_def.get('kpi_value', 10)))
    except Exception:
        aaa_min_games = 10

    free_def = kpi_map.get('FREE_GAME_RULE', DEFAULT_KPI_DEFINITIONS['FREE_GAME_RULE'])
    free_params = _parse_params(free_def.get('params_json'))
    free_max_price = float(free_params.get('max_price', 0.0))
    free_include_100 = bool(free_params.get('include_100_discount', False))
    if str(free_def.get('kpi_value', '')).upper() == 'INCLUDE_100_DISCOUNT':
        free_include_100 = True

    ratio_def = kpi_map.get('POSITIVE_RATIO_FORMULA', DEFAULT_KPI_DEFINITIONS['POSITIVE_RATIO_FORMULA'])
    ratio_params = _parse_params(ratio_def.get('params_json'))
    ratio_formula = str(ratio_def.get('kpi_value', 'STANDARD')).upper()
    if ratio_formula not in ('STANDARD', 'LAPLACE_SMOOTHED'):
        ratio_formula = 'STANDARD'
    ratio_min_reviews = int(ratio_params.get('min_reviews', 1))
    ratio_alpha = float(ratio_params.get('alpha', 0.0))

    return {
        # Validation rule flags for dbt cleaning & tests
        'rule_price_non_negative': rule_map.get('PRICE_NON_NEGATIVE', True),
        'rule_discount_range': rule_map.get('DISCOUNT_RANGE', True),
        'rule_metacritic_range': rule_map.get('METACRITIC_RANGE', True),
        # KPI definitions
        'kpi_publisher_aaa_min_games': max(1, aaa_min_games),
        'kpi_free_max_price': free_max_price,
        'kpi_free_include_100_discount': free_include_100,
        'kpi_positive_ratio_formula': ratio_formula,
        'kpi_positive_ratio_min_reviews': max(1, ratio_min_reviews),
        'kpi_positive_ratio_alpha': max(0.0, ratio_alpha),
    }


def compute_config_hash(rules, kpis):
    """Deterministic SHA-256 hash of dbt-affecting rule/KPI vars for recompute detection."""
    payload = build_dbt_vars(rules, kpis)
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode('utf-8')).hexdigest()


def get_applied_config_hash(connection):
    if connection is None:
        return None
    try:
        if connection.execute("SELECT OBJECT_ID('dbo.etl_metadata_state', 'U')").fetchone()[0] is None:
            return None
        row = connection.execute(
            "SELECT state_value FROM dbo.etl_metadata_state WHERE state_key = 'LAST_APPLIED_CONFIG_HASH'"
        ).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def set_applied_config_hash(connection, config_hash):
    if connection is None or not config_hash:
        return
    if connection.execute("SELECT OBJECT_ID('dbo.etl_metadata_state', 'U')").fetchone()[0] is None:
        return
    connection.execute("""
        MERGE dbo.etl_metadata_state AS target
        USING (SELECT 'LAST_APPLIED_CONFIG_HASH' AS state_key, ? AS state_value) AS src
        ON target.state_key = src.state_key
        WHEN MATCHED THEN
            UPDATE SET state_value = src.state_value, updated_at = SYSUTCDATETIME()
        WHEN NOT MATCHED THEN
            INSERT (state_key, state_value) VALUES (src.state_key, src.state_value);
    """, config_hash)
