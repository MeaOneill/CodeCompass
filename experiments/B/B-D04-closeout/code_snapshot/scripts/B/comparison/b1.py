"""Direct B1 Responses adapter, one format-only repair, auditable call accounting.

Transport injection is for labelled tests; it is never a real-model fallback.
No endpoint redirect, tools, server conversation, automatic retry or secrets in logs.
"""
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen, build_opener, HTTPRedirectHandler


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


class SpendMeter:
    def __init__(self, budget):
        self.budget = budget; self.reserved = 0.0

    def reserve(self, amount):
        if type(amount) not in (int, float) or not math.isfinite(amount) or amount <= 0:
            raise ValueError('Positive per-call reservation required')
        if self.reserved+amount > self.budget+1e-12: return False
        self.reserved += amount
        return True


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def api_transport(payload, config):
    if config['endpoint'] != 'https://api.openai.com/v1/responses':
        raise ValueError('Only the reviewed official Responses endpoint is supported')
    key = os.environ[config['api_key_env']]
    request = Request(config['endpoint'], data=json.dumps(payload).encode(),
                      headers={'Authorization': 'Bearer '+key, 'Content-Type': 'application/json'})
    # Never copy response/error headers or credentials into artifacts.
    with build_opener(NoRedirect()).open(request, timeout=config['timeout_seconds']) as response:
        raw = response.read(config['max_response_bytes']+1)
    if len(raw) > config['max_response_bytes']: raise ValueError('RESPONSE_TOO_LARGE')
    return json.loads(raw)


def inspect_raw(raw, key=None):
    text = json.dumps(raw, ensure_ascii=False)
    if (key and key in text) or re.search(r'(?i)sk-[a-z0-9_-]{12,}|[\w.+-]+@[\w.-]+\.[a-z]{2,}|-----BEGIN .*PRIVATE KEY', text):
        return {'quarantined': True, 'raw_sha256': hashlib.sha256(text.encode()).hexdigest(),
                'reason': 'Potential secret/contact; raw not exported to Git artifacts'}
    return {'quarantined': False, 'response': raw, 'raw_sha256': hashlib.sha256(text.encode()).hexdigest()}


def parse_route(text):
    obj = json.loads(text)
    if not isinstance(obj, dict) or set(obj) != {'ordered_units'}:
        raise ValueError('Return exactly one object with ordered_units')
    route = obj['ordered_units']
    if not isinstance(route, list) or not all(isinstance(s, str) for s in route):
        raise ValueError('ordered_units must be an array of strings')
    return route


def run_b1(context, config, prompt, meter, *, transport=None):
    calls = []; injected = transport is not None
    result = {'attempted': False, 'status': 'NOT_CONFIGURED', 'route': None,
              'calls': calls, 'transport_is_fixture': injected, 'model_requested': config.get('model')}
    required = ['model', 'budget_usd', 'per_call_reservation_usd', 'price_source']
    if not config.get('enabled') or any(config.get(k) is None for k in required): return result
    for k in ['budget_usd', 'input_usd_per_million', 'output_usd_per_million', 'timeout_seconds']:
        if type(config.get(k)) not in (int, float) or not math.isfinite(config[k]) or config[k] < 0:
            raise ValueError('Finite configured budget/rates/time required: '+k)
    if config.get('max_repairs') != 1: raise ValueError('D04 format repair policy is fixed at one')
    if not injected and not os.environ.get(config['api_key_env']): return result
    if set(config.get('params', {})) - {'reasoning', 'temperature', 'top_p'}:
        raise ValueError('Parameters cannot override model, input, tools or budget')
    transport = transport or api_transport
    base = prompt+'\nCONTEXT_JSON\n'+json.dumps(context, ensure_ascii=False, sort_keys=True)
    text_input = base
    for attempt in range(2):
        if not meter.reserve(config['per_call_reservation_usd']):
            result['status'] = 'BUDGET_EXHAUSTED' if calls else 'BUDGET_NOT_RUN'; return result
        payload = {'model': config['model'], 'input': text_input, 'store': False,
                   'max_output_tokens': config['max_output_tokens'], **config.get('params', {})}
        started = time.perf_counter()
        call = {'attempt': attempt, 'kind': 'initial' if attempt == 0 else 'format_repair',
                'timestamp': datetime.now(timezone.utc).isoformat(), 'request_hash': digest(payload),
                'request': payload, 'configured_rates': {k:config[k] for k in ['input_usd_per_million', 'output_usd_per_million', 'price_source']},
                'model_requested': config['model'], 'model_returned': None, 'usage': None,
                'estimated_cost_usd': None, 'billing_cost_usd': None, 'reserved_usd': config['per_call_reservation_usd']}
        calls.append(call); result['attempted'] = True
        try:
            raw = transport(payload, config)
            call.update(inspect_raw(raw, os.environ.get(config['api_key_env'])))
            if call['quarantined']:
                result['status'] = 'PRIVACY_QUARANTINED'; return result
            call['model_returned'] = raw.get('model'); call['usage'] = raw.get('usage')
            usage = raw.get('usage') or {}
            if all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('input_tokens', 'output_tokens')):
                call['estimated_cost_usd'] = (usage['input_tokens']*config['input_usd_per_million'] + usage['output_tokens']*config['output_usd_per_million'])/1e6
            if raw.get('model') != config['model']:
                result['status'] = 'MODEL_MISMATCH'; return result
            if raw.get('status') != 'completed':
                result['status'] = 'API_INCOMPLETE'; return result
            if call['estimated_cost_usd'] is None:
                result['status'] = 'USAGE_MISSING'; return result
            if call['estimated_cost_usd'] > config['per_call_reservation_usd']:
                result['status'] = 'COST_RESERVATION_EXCEEDED'; return result
            text = ''.join(part['text'] for item in raw.get('output', []) if item.get('type') == 'message'
                           for part in item.get('content', []) if part.get('type') == 'output_text')
            try:
                result['route'] = parse_route(text)
                result['status'] = 'PARSED'; return result
            except (ValueError, TypeError) as e:
                call['format_error'] = str(e)
                if attempt == 1:
                    result['status'] = 'FORMAT_ERROR'; return result
                # No correctness hints, gate output, benchmark answers or other routes.
                text_input = base+'\nFORMAT_ONLY_REPAIR: Return {"ordered_units": [string,...]} only. Preserve the intended order. Prior output:\n'+text
        except (TimeoutError,):
            result['status'] = 'TIMEOUT'; return result
        except HTTPError as e:
            call['error'] = 'HTTP_'+str(e.code); result['status'] = 'API_ERROR'; return result
        except URLError as e:
            call['error'] = type(e.reason).__name__
            result['status'] = 'TIMEOUT' if isinstance(e.reason, TimeoutError) else 'API_ERROR'
            return result
        except (URLError, OSError, ValueError, KeyError, TypeError) as e:
            call['error'] = type(e).__name__; result['status'] = 'API_ERROR'; return result
        finally:
            call['elapsed_seconds'] = time.perf_counter()-started
    return result
