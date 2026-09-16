"""Bounded local retrieval. Metadata JSON arrays keep parsing dependency-free."""
import json
from pathlib import Path


def metadata(path):
    out = {}
    with Path(path).open() as stream:
        if stream.readline().strip() != '---': return out
        for number, line in enumerate(stream):
            if line.strip() == '---' or number >= 60: break
            if ':' not in line: continue
            k, v = line.split(':', 1)
            try: out[k] = json.loads(v.strip())
            except ValueError: out[k] = v.strip().strip("\"'")
    return out


def search(root, query, details=False):
    """Return executable summaries; load contract bodies only on explicit request."""
    matches = []
    for path in (root / "references/capabilities").glob("**/*.md"):
        meta = metadata(path)
        if any(term.casefold() in query.casefold() for term in meta.get('exclude_keywords', [])):
            continue
        terms = [meta.get("id", ""), *meta.get("keywords", [])]
        score = sum(len(t) for t in terms if t and t.casefold() in query.casefold())
        if score: matches.append((score, path, meta))
    result = []
    included_workflows = set()
    best = max((m[0] for m in matches), default=0)
    relevant = [m for m in matches if m[0] >= max(2, best * 0.6)]
    for _, path, meta in sorted(relevant, key=lambda v: (-v[0], str(v[1])))[:3]:
        item = {k: meta[k] for k in ('id', 'service', 'status', 'transport', 'command', 'requests', 'note') if k in meta}
        item['file'] = str(path)
        if details:
            content = path.read_text()
            item['content'] = content[:5000]
            if len(content) > 5000: item['content_truncated'] = True
        if meta.get('workflow'):
            workflow = (root / meta['workflow']).resolve()
            if workflow.is_relative_to(root.resolve()) and workflow.is_file():
                item['workflow_file'] = str(workflow)
                if details and workflow not in included_workflows:
                    content = workflow.read_text()
                    item['workflow'] = content[:4000]
                    if len(content) > 4000: item['workflow_truncated'] = True
                    included_workflows.add(workflow)
        result.append(item)
    routes = []
    if not result:
        for entry in json.loads((root / 'references/services.json').read_text()).get('services', []):
            if any(term.casefold() in query.casefold() for term in [entry['id'], *entry['aliases']]):
                routes.append(entry)
    return {'matches': result, 'service_candidates': routes[:3],
            'next': None if result else 'No capability matched. Resolve this business service only; do not start client/UI setup.'}


def capability(root, name):
    found = [metadata(p) for p in (root / "references/capabilities").glob("**/*.md") if p.stem == name]
    if len(found) != 1: raise ValueError("Capability missing or ambiguous")
    return found[0]
