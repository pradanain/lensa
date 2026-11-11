"""Physical project layout and relative links used by document generators."""
from pathlib import Path
import posixpath
import re


DOCUMENTS = {
    **{name: 'docs/analytics/' + name for name in (
        'ANALYTICAL_CAPABILITIES.md', 'ANALYTICAL_DEVELOPMENT_ROADMAP.md')},
    **{name: 'docs/reference/' + name for name in (
        'DATA_ARCHITECTURE.md', 'DATA_RELATIONSHIPS.md', 'ENTITY_RELATIONSHIP_DIAGRAM.md',
        'DATASET_CATALOG.md', 'DATA_ACCESS_POLICY.md')},
    **{name: 'docs/history/' + name for name in (
        'WORKSPACE_INVENTORY.md', 'WORKSPACE_REORGANIZATION_PLAN.md', 'DEVELOPMENT_ROADMAP.md')},
}


def report_group(name):
    if name == 'README.md':
        return ''
    if name.startswith('analytical_'):
        return 'readiness'
    if name == 'PROJECT_CLEANUP_VALIDATION.md':
        return 'project_cleanup'
    if name.startswith(('UB_', 'ub_')):
        return 'ub'
    if name.startswith(('P1_', 'p1_')):
        return 'p1'
    if name.startswith(('EXPORT_', 'export_', 'count_', 'blocker_')):
        return 'reconciliation'
    if name.startswith(('database_', 'data_quality_', 'DATA_QUALITY_', 'mart_', 'relationship_', 'unmatched_')):
        return 'database'
    if name.startswith(('initial_', 'idempotency_', 'last_sync', 'sync_')):
        return 'sync'
    return 'integration'


def relocate(relative):
    """Map a logical pre-layout path; source-data paths remain untouched."""
    path = str(relative).replace('\\', '/')
    if path == 'scripts/history':
        return 'archive/project_history/scripts'
    if path == 'sql/history':
        return 'archive/project_history/sql'
    if path.startswith('scripts/history/'):
        return 'archive/project_history/scripts/' + path[len('scripts/history/'):]
    if path.startswith('sql/history/'):
        return 'archive/project_history/sql/' + path[len('sql/history/'):]
    first, _, rest = path.partition('/')
    if first in ('src', 'scripts', 'sql', 'config', 'tests'):
        return 'app/' + path
    if first == 'metadata':
        return 'data/' + path
    if first == 'docs' and rest in DOCUMENTS:
        return DOCUMENTS[rest]
    if first == 'reports':
        name = rest.split('/')[0]
        if not rest:
            return 'docs/reports'
        if name in ('analytics', 'project_cleanup'):
            return 'docs/' + path
        if name == 'sync_batches':
            return 'docs/reports/sync/' + rest
        group = report_group(name)
        return 'docs/reports/' + (group + '/' if group else '') + rest
    return path


def original_document(relative):
    path = str(relative).replace('\\', '/')
    for name, new in DOCUMENTS.items():
        if path == new:
            return 'docs/' + name
    if path.startswith('docs/reports/'):
        tail = path[len('docs/reports/'):]
        if tail.split('/')[0] in ('analytics', 'project_cleanup'):
            return 'reports/' + tail
        if '/' in tail:
            return 'reports/' + tail.split('/', 1)[1]
        return 'reports/' + tail
    return path


def rebase_markdown(text, original, destination=None):
    destination = destination or relocate(original)
    def replace(match):
        target = match[1]
        if target.startswith(('#', '/')) or re.match(r'^[a-zA-Z]+:', target):
            return match[0]
        wrapped = target.startswith('<') and target.endswith('>')
        raw = target[1:-1] if wrapped else target
        path, separator, anchor = raw.partition('#')
        old_absolute = posixpath.normpath(posixpath.join(posixpath.dirname(original), path))
        new_absolute = relocate(old_absolute)
        relative = posixpath.relpath(new_absolute, posixpath.dirname(destination) or '.')
        result = relative + (separator + anchor if separator else '')
        return '](' + ('<' + result + '>' if wrapped else result) + ')'
    return re.sub(r'\]\(([^)]+)\)', replace, text)


def write_document(root, logical_path, text):
    target = Path(root) / relocate(logical_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rebase_markdown(text, logical_path), encoding='utf-8')
    return target
