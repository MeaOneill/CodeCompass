"""Read-only public Issue snapshots and conservative module matching, owned by B."""
from datetime import datetime, timezone
import hashlib
import json
import re
from urllib.request import Request, urlopen


def fetch_snapshot(repo='mahmoud/boltons', *, per_page=50):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('Expected owner/repository')
    if type(per_page) is not int or not 1 <= per_page <= 100:
        raise ValueError('per_page must be in 1..100')
    url = f'https://api.github.com/repos/{repo}/issues?state=all&per_page={per_page}&sort=updated&direction=desc'
    req = Request(url, headers={'Accept': 'application/vnd.github+json', 'User-Agent': 'CodeCompass-B-D03-readonly'})
    with urlopen(req, timeout=30) as response:
        body = response.read()
        status = response.status
        server_date = response.headers.get('Date')
    data = json.loads(body)
    if not isinstance(data, list):
        raise ValueError('GitHub list response required')
    issues = []
    for row in data:
        if 'pull_request' in row:
            continue

        issues.append({k: row.get(k) for k in (
            'number', 'title', 'html_url', 'state', 'state_reason',
            'created_at', 'updated_at', 'closed_at', 'body')})
    return {'snapshot_version': 'B-D03-1', 'repo': repo, 'source_url': url,
            'retrieved_at': datetime.now(timezone.utc).isoformat(), 'server_date': server_date,
            'http_status': status, 'response_sha256': hashlib.sha256(body).hexdigest(),
            'source_mode': 'LIVE_FETCH_SAVED_SNAPSHOT', 'is_fixture': False,
            'pagination': {'per_page': per_page, 'pages_fetched': 1, 'complete_repository': False},
            'privacy': 'Public issue text/metadata; no authors, contacts, comments or answers.',
            'issues': issues}


def match_issues(snapshot, units, gaps):
    """Module tokens imply a review candidate, never suitability or accuracy."""
    if snapshot.get('snapshot_version') != 'B-D03-1' or type(snapshot.get('is_fixture')) is not bool:
        raise ValueError('Unsupported or unlabelled snapshot')
    repo = snapshot['repo']
    candidates, historical, unmatched = [], [], []
    modules = {}
    for unit in units:
        for span in unit['source_spans']:
            path = span['path']
            token = path.rsplit('/', 1)[-1].removesuffix('.py').lower()
            modules.setdefault(token, {'path': path, 'unit_ids': [], 'concept_ids': []})
            modules[token]['unit_ids'].append(unit['id'])
            modules[token]['concept_ids'].extend(unit['concept_ids'])
    for issue in snapshot['issues']:
        if issue['html_url'] != f'https://github.com/{repo}/issues/{issue["number"]}':
            raise ValueError('Issue URL/repository mismatch')
        if issue['state'] not in ('open', 'closed'):
            raise ValueError('Unknown Issue state')
        text = (issue['title'] + '\n' + (issue.get('body') or '')).lower()
        hits = [m for token, m in modules.items() if re.search(r'(?<![a-z0-9_])' + re.escape(token) + r'(?![a-z0-9_])', text)]
        entry = {'number': issue['number'], 'url': issue['html_url'], 'title': issue['title'],
                 'state_at_capture': issue['state'], 'retrieved_at': snapshot['retrieved_at'],
                 'is_fixture': snapshot['is_fixture'], 'source_mode': 'FIXTURE' if snapshot['is_fixture'] else 'FIXED_PUBLIC_SNAPSHOT',
                 'modules': sorted({m['path'] for m in hits}),
                 'candidate_concept_gaps': sorted(set(gaps) & {c for m in hits for c in m['concept_ids']}),
                 'relevance_label': 'UNREVIEWED_TOKEN_MATCH' if hits else 'NO_MODULE_TOKEN_MATCH',
                 'reason': 'Module token in public title/body; semantic relevance and version applicability need review.' if hits else 'No covered module token in this limited snapshot.',
                 'version_gap': 'Issue current state is separate from pinned source commit; reproduction not performed.',
                 'preparation_steps': [
                     'Recheck original URL and current state before any work.',
                     'Compare the reported function against the pinned source; shared module is insufficient.',
                     'Reproduce in an isolated checkout, add a failing regression and record environment/commit.',
                     'Review contribution rules and overlapping PRs before a member decides whether to submit.'
                 ],
                 'community_submission': False}
        if issue['state'] == 'closed':
            entry['disposition'] = 'HISTORICAL_CLOSED_NOT_ACTIONABLE'
            historical.append(entry)
        elif hits:
            entry['disposition'] = 'OPEN_REVIEW_CANDIDATE_NOT_CONFIRMED'
            candidates.append(entry)
        else:
            entry['disposition'] = 'UNMATCHED'
            unmatched.append(entry)
    return {'snapshot_retrieved_at': snapshot['retrieved_at'], 'is_fixture': snapshot['is_fixture'],
            'candidates': candidates, 'historical': historical, 'unmatched': unmatched,
            'no_suitable_reason': None if candidates else 'No open module-token candidate in the fetched page; this is not an exhaustive repository search.',
            'independent_relevance_labels': 0, 'recommendation_accuracy': None,
            'formal_study_result': False}
