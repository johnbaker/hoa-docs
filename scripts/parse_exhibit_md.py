#!/usr/bin/env python3
import json
import re
from pathlib import Path
import tempfile
from datetime import datetime, timezone


def extract_header(text: str):
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return {}, text
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == '---':
            end_idx = i
            break
    if end_idx is None:
        return {}, text
    header_lines = lines[1:end_idx]
    body_lines = lines[end_idx + 1:]
    meta = {}
    for line in header_lines:
        if not line.strip():
            continue
        if ':' not in line:
            continue
        key, value = line.split(':', 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if value.lower() == 'true':
            parsed = True
        elif value.lower() == 'false':
            parsed = False
        elif len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            parsed = value[1:-1]
        else:
            parsed = value
        meta[key] = parsed
    return meta, "\n".join(body_lines)


def parse_text(text: str, *, node_prefix: str, included_in_instrument_id: str | None = None):
    lines_raw = text.splitlines()

    # Split only when a new row starts on the same line (i.e., another non-space follows).
    row_split_re = re.compile(r'\|\s*\|\s*(?=\S)')
    lines = []
    for line in lines_raw:
        if '|' in line and row_split_re.search(line):
            expanded = row_split_re.sub('|\n|', line)
            lines.extend(expanded.splitlines())
        else:
            lines.append(line)

    nodes = []
    node_by_id = {}
    incorporations = []

    root_id = f'node:{node_prefix}:root'
    root = {
        'id': root_id,
        'type': 'document',
        'children': []
    }
    node_by_id[root_id] = root
    nodes.append(root)

    pending_dest = None
    pending_table_label = None
    current_indent = None
    pending_exhibit_id = None
    pending_exhibit_title = False
    epilog_mode = False
    current_exhibit_id = None
    list_item_section_parent = None
    list_item_section_indent = None

    section_stack = {}
    current_top_num = None
    para_counters = {}
    list_counters = {}
    table_counters = {}

    def add_node(node, parent_id=None):
        node_id = node['id']
        nodes.append(node)
        node_by_id[node_id] = node
        if parent_id:
            parent = node_by_id[parent_id]
            parent.setdefault('children', []).append({'ref': node_id})

    def next_para_id(parent_id):
        count = para_counters.get(parent_id, 0) + 1
        para_counters[parent_id] = count
        return f"{parent_id}:p-{count}"

    def next_list_id(parent_id):
        count = list_counters.get(parent_id, 0) + 1
        list_counters[parent_id] = count
        return f"{parent_id}:list-{count}"

    def next_table_id(parent_id):
        count = table_counters.get(parent_id, 0) + 1
        table_counters[parent_id] = count
        return f"{parent_id}:table-{count}"

    def make_meta():
        meta = {}
        nonlocal pending_dest
        if pending_dest:
            meta['pdf_dest'] = {'name': pending_dest}
            pending_dest = None
        if current_indent is not None:
            meta['indent_level'] = current_indent
        return meta

    heading_re = re.compile(r'^(#+)\s*(.+?)\s*$')
    chapter_re = re.compile(r'^Chapter\s+(\d+)\s*(.*)$', re.IGNORECASE)
    num_heading_re = re.compile(r'^(\d+(?:\.\d+)+)\s*(.*)$')
    exhibit_re = re.compile(r'^@exhibit\s+(.+)$', re.IGNORECASE)
    exhibit_instrument_re = re.compile(r'\s+@instrument(?:_id)?\s+([A-Za-z0-9._:-]+)\s*$', re.IGNORECASE)
    exhibit_base_doc_re = re.compile(r'\s+@base_doc(?:_id)?\s+([A-Za-z0-9._-]+)\s*$', re.IGNORECASE)
    base_doc_id_re = re.compile(r'^[a-z0-9][a-z0-9._-]{0,63}$')

    table_label_re = re.compile(r'^#\s*Table\s+(.+?)\s*#\s*$')

    list_item_re = re.compile(r'^(\s*)([-+*]|\d+[.)]|[a-zA-Z][.)]|\.\d+)\s+(.*)$')
    inline_label_re = re.compile(r'^(\([a-zA-Z0-9]+\)|[a-zA-Z0-9]+\.)\s+(.*)$')
    inline_decimal_label_re = re.compile(r'^(\.\d+)\s+(.*)$')

    list_stack = []

    def current_section_parent():
        if section_stack:
            return section_stack.get(max(section_stack.keys(), default=0), root_id)
        return current_exhibit_id or root_id

    def close_lists(to_indent=None):
        while list_stack and (to_indent is None or list_stack[-1]['indent'] >= to_indent):
            list_stack.pop()

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if pending_exhibit_id and pending_exhibit_title and not stripped.startswith('#'):
            pending_exhibit_id = None
            pending_exhibit_title = False

        if stripped.startswith('@') and stripped.lower() != '@epilog':
            epilog_mode = False
            list_item_section_parent = None
            list_item_section_indent = None

        if stripped.lower() == '@epilog':
            close_lists()
            epilog_mode = True
            section_stack = {}
            current_top_num = None
            current_exhibit_id = None
            list_item_section_parent = None
            list_item_section_indent = None
            i += 1
            continue

        if stripped.startswith('>>> '):
            pending_dest = stripped[4:].strip().lstrip('/')
            i += 1
            continue

        if stripped.startswith(']]]'):
            indent_level = len(stripped) // 3
            current_indent = indent_level
            i += 1
            continue

        m_label = table_label_re.match(stripped)
        if m_label:
            pending_table_label = f"Table {m_label.group(1)}"
            i += 1
            continue

        m_ex = exhibit_re.match(stripped)
        if m_ex:
            close_lists()
            label = m_ex.group(1).strip()
            instrument_id = None
            base_doc_id = None
            m_ex_ref = exhibit_instrument_re.search(label)
            if m_ex_ref:
                instrument_id = m_ex_ref.group(1)
                label = label[:m_ex_ref.start()].strip()
            m_base_ref = exhibit_base_doc_re.search(label)
            if m_base_ref:
                base_doc_id = m_base_ref.group(1)
                label = label[:m_base_ref.start()].strip()
            parent_id = root_id
            exhibit_id = f"node:{node_prefix}:exhibit-{len([n for n in nodes if n['type']=='exhibit'])+1}"
            node = {'id': exhibit_id, 'type': 'exhibit', 'label': label, 'children': []}
            meta = make_meta()
            if instrument_id or base_doc_id:
                meta = meta or {}
                ref = {}
                if instrument_id:
                    ref['instrument_id'] = instrument_id
                if base_doc_id:
                    ref['base_doc_id'] = base_doc_id
                meta['exhibit_ref'] = ref
                if included_in_instrument_id:
                    inc_base_doc_id = base_doc_id
                    if not inc_base_doc_id and instrument_id and base_doc_id_re.match(instrument_id):
                        inc_base_doc_id = instrument_id
                    if inc_base_doc_id:
                        incorporations.append({
                            'role': 'exhibit',
                            'exhibit_label': label,
                            'base_doc_id': inc_base_doc_id,
                            'included_in_instrument_id': included_in_instrument_id,
                        })
            if meta:
                node['meta'] = meta
            add_node(node, parent_id)
            pending_exhibit_id = exhibit_id
            current_exhibit_id = exhibit_id
            section_stack = {}
            current_top_num = None
            current_indent = None
            i += 1
            continue

        m = heading_re.match(stripped)
        if m:
            hashes, text = m.groups()
            leading_spaces = len(line) - len(line.lstrip(' '))
            if list_stack and list_stack[-1]['last_item_id'] and leading_spaces > list_stack[-1]['indent']:
                m_ch = chapter_re.match(text)
                m_num = num_heading_re.match(text)
                node_type = 'section'
                label = None
                title = None
                if m_ch:
                    chap_num = int(m_ch.group(1))
                    label = f"Chapter {chap_num}"
                    title = m_ch.group(2).strip() or None
                elif m_num:
                    num_label = m_num.group(1)
                    title = m_num.group(2).strip() or None
                    label = num_label
                    dot_count = num_label.count('.')
                    node_type = 'section' if dot_count <= 1 else 'subsection'
                else:
                    title = text

                if label:
                    norm = label.lower().replace('chapter ', 'chapter-').replace('.', '-').replace(' ', '-')
                else:
                    norm = title.lower().replace(' ', '-') if title else 'section'
                norm = re.sub(r'[^a-z0-9\-]+', '-', norm).strip('-')
                node_id = f"node:{node_prefix}:{norm}"
                suffix = 1
                base_id = node_id
                while node_id in node_by_id:
                    suffix += 1
                    node_id = f"{base_id}-{suffix}"

                node = {'id': node_id, 'type': node_type}
                if label:
                    node['label'] = label
                if title:
                    node['title'] = title
                meta = make_meta()
                if meta:
                    node['meta'] = meta
                add_node(node, list_stack[-1]['last_item_id'])
                list_item_section_parent = node_id
                list_item_section_indent = leading_spaces
                current_indent = None
                i += 1
                continue

            close_lists()
            list_item_section_parent = None
            list_item_section_indent = None
            if pending_exhibit_id:
                current_title = node_by_id[pending_exhibit_id].get('title')
                if current_title:
                    node_by_id[pending_exhibit_id]['title'] = f"{current_title} {text}".strip()
                else:
                    node_by_id[pending_exhibit_id]['title'] = text
                pending_exhibit_title = True
                current_indent = None
                i += 1
                continue
            level = len(hashes)
            if level == 1:
                node_id = f"node:{node_prefix}:heading-{len([n for n in nodes if n['type']=='heading'])+1}"
                node = {'id': node_id, 'type': 'heading', 'text': text}
                meta = make_meta()
                if meta:
                    node['meta'] = meta
                add_node(node, root_id)
            else:
                m_ch = chapter_re.match(text)
                m_num = num_heading_re.match(text)
                depth = None
                node_type = 'section'
                label = None
                title = None
                if m_ch:
                    chap_num = int(m_ch.group(1))
                    current_top_num = chap_num
                    label = f"Chapter {chap_num}"
                    title = m_ch.group(2).strip() or None
                    depth = 1
                    node_type = 'section'
                elif m_num:
                    num_label = m_num.group(1)
                    title = m_num.group(2).strip() or None
                    label = num_label
                    first_num = int(num_label.split('.')[0])
                    dot_count = num_label.count('.')
                    depth = dot_count + 1
                    if current_top_num != first_num:
                        depth = 1
                        current_top_num = first_num
                    node_type = 'section' if depth == 1 or depth == 2 else 'subsection'
                else:
                    # Use markdown heading level to set section depth deterministically.
                    depth = max(1, level - 1)
                    node_type = 'subsection' if depth > 1 else 'section'
                    title = text

                base_parent = current_exhibit_id or root_id
                parent_id = base_parent if depth == 1 else section_stack.get(depth - 1, base_parent)

                if label:
                    norm = label.lower().replace('chapter ', 'chapter-').replace('.', '-').replace(' ', '-')
                else:
                    norm = title.lower().replace(' ', '-') if title else 'section'
                norm = re.sub(r'[^a-z0-9\-]+', '-', norm).strip('-')
                node_id = f"node:{node_prefix}:{norm}"
                suffix = 1
                base_id = node_id
                while node_id in node_by_id:
                    suffix += 1
                    node_id = f"{base_id}-{suffix}"

                node = {'id': node_id, 'type': node_type}
                if label:
                    node['label'] = label
                if title:
                    node['title'] = title
                meta = make_meta()
                if meta:
                    node['meta'] = meta
                add_node(node, parent_id)

                for d in list(section_stack.keys()):
                    if d >= depth:
                        section_stack.pop(d, None)
                section_stack[depth] = node_id

            current_indent = None
            i += 1
            continue

        if stripped.startswith('|'):
            close_lists()
            table_lines = []
            while i < len(lines):
                l = lines[i].strip()
                if not l.startswith('|'):
                    break
                table_lines.append(l)
                i += 1

            def split_row(row):
                row = row.strip()
                if row.startswith('|'):
                    row = row[1:]
                if row.endswith('|'):
                    row = row[:-1]
                return [cell.strip() for cell in row.split('|')]

            columns = None
            rows = []
            if len(table_lines) >= 2:
                sep_line = table_lines[1]
                # Treat only dashed separator rows as headers, not empty rows.
                if '-' in sep_line and re.match(r'^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$', sep_line):
                    columns = split_row(table_lines[0])
                    for row in table_lines[2:]:
                        if row.strip():
                            rows.append(split_row(row))
                else:
                    for row in table_lines:
                        rows.append(split_row(row))
            elif table_lines:
                rows.append(split_row(table_lines[0]))

            parent_id = root_id if epilog_mode else current_section_parent()
            table_id = next_table_id(parent_id)
            node = {'id': table_id, 'type': 'table', 'rows': rows}
            if columns:
                node['columns'] = columns
            if pending_table_label:
                node['label'] = pending_table_label
                pending_table_label = None
            meta = make_meta()
            if meta:
                node['meta'] = meta
            add_node(node, parent_id)
            current_indent = None
            continue

        m_list = list_item_re.match(line)
        if m_list:
            indent_str, marker, item_text = m_list.groups()
            indent = len(indent_str.expandtabs(2))

            while list_stack and indent < list_stack[-1]['indent']:
                list_stack.pop()

            if not list_stack or indent > list_stack[-1]['indent']:
                parent_id = root_id if epilog_mode else current_section_parent()
                if list_stack:
                    parent_id = list_stack[-1]['last_item_id']
                list_id = next_list_id(parent_id)
                list_node = {'id': list_id, 'type': 'list', 'children': []}
                add_node(list_node, parent_id)
                list_stack.append({'indent': indent, 'list_id': list_id, 'last_item_id': None})

            list_id = list_stack[-1]['list_id']
            item_id = next_para_id(list_id)
            list_item_section_parent = None
            list_item_section_indent = None
            item_node = {'id': item_id, 'type': 'list_item', 'text': item_text}
            label = None
            if marker not in ('-', '+', '*'):
                label = marker
            else:
                inline = inline_label_re.match(item_text)
                if inline:
                    label = inline.group(1)
                    item_text = inline.group(2)
                    item_node['text'] = item_text
                else:
                    inline_decimal = inline_decimal_label_re.match(item_text)
                    if inline_decimal:
                        label = inline_decimal.group(1)
                        item_text = inline_decimal.group(2)
                        item_node['text'] = item_text
            if label:
                item_node['label'] = label
            if '::' in item_text:
                title_part, text_part = item_text.split('::', 1)
                title_part = title_part.strip()
                text_part = text_part.strip()
                if title_part:
                    item_node['title'] = title_part
                    item_node['text'] = text_part
            meta = make_meta()
            if meta:
                item_node['meta'] = meta
            add_node(item_node, list_id)
            list_stack[-1]['last_item_id'] = item_id
            current_indent = None
            i += 1
            continue

        if list_stack:
            leading_spaces = len(line) - len(line.lstrip(' '))
            if leading_spaces > list_stack[-1]['indent'] and list_stack[-1]['last_item_id']:
                parent_id = list_stack[-1]['last_item_id']
                if list_item_section_parent and list_item_section_indent is not None:
                    if leading_spaces >= list_item_section_indent:
                        parent_id = list_item_section_parent
                para_id = next_para_id(parent_id)
                node = {'id': para_id, 'type': 'paragraph', 'text': stripped}
                meta = make_meta()
                if meta:
                    node['meta'] = meta
                add_node(node, parent_id)
                current_indent = None
                i += 1
                continue

        close_lists()
        list_item_section_parent = None
        list_item_section_indent = None
        parent_id = root_id if epilog_mode else current_section_parent()
        node_id = next_para_id(parent_id)
        node = {'id': node_id, 'type': 'paragraph', 'text': stripped}
        meta = make_meta()
        if meta:
            node['meta'] = meta
        add_node(node, parent_id)
        current_indent = None
        i += 1

    generated_at = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    result = {
        'content': {
            'schema_version': 1,
            'root_ref': root_id,
            'nodes': nodes,
            'meta': {
                'generated_at': generated_at
            }
        }
    }
    if incorporations:
        result['incorporations'] = incorporations
    return result


def infer_node_prefix(existing):
    content = existing.get('content') or {}
    root_ref = content.get('root_ref') or ''
    match = re.match(r'^node:([^:]+):', root_ref)
    if match:
        return match.group(1)
    return None


def strip_content(data):
    return {k: v for k, v in data.items() if k != 'content'}


def build_instrument(meta, args):
    def pick(key, arg_name=None):
        arg_name = arg_name or key
        value = getattr(args, arg_name, None)
        if value is not None:
            return value
        return meta.get(key)

    def pick_bool(key, arg_name=None):
        value = pick(key, arg_name)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() == 'true':
                return True
            if value.lower() == 'false':
                return False
        return value

    availability_has_text = pick_bool('availability_has_text')
    availability_reason = pick('availability_reason')
    instrument = {
        'id': pick('instrument_id', 'instrument_id'),
        'base_doc_id': pick('base_doc_id', 'base_doc_id'),
        'title': pick('title', 'title'),
        'instrument_kind': pick('instrument_kind', 'instrument_kind'),
        'doc_type': pick('doc_type', 'doc_type'),
        'jurisdiction': pick('jurisdiction', 'jurisdiction'),
        'recorded_at': pick('recorded_at', 'recorded_at'),
        'effective_at': pick('effective_at', 'effective_at'),
        'recording': {
            'county': pick('recording_county', 'recording_county'),
            'state': pick('recording_state', 'recording_state'),
            'book': pick('recording_book', 'recording_book'),
            'page': pick('recording_page', 'recording_page')
        },
        'availability': {
            'has_text': True if availability_has_text is None else availability_has_text,
            'reason': availability_reason or 'available'
        }
    }
    missing = []
    for key in [
        'id', 'base_doc_id', 'title', 'instrument_kind', 'doc_type',
        'jurisdiction', 'recorded_at', 'effective_at'
    ]:
        if not instrument.get(key):
            missing.append(key)
    for key in ['county', 'state', 'book', 'page']:
        if not instrument['recording'].get(key):
            missing.append(f"recording_{key}")
    if missing:
        missing_args = ', '.join(missing)
        raise SystemExit(f'Missing required instrument fields: {missing_args}')
    return instrument


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Parse markdown into instrument JSON.')
    parser.add_argument('source', help='Path to markdown source file.')
    parser.add_argument('output', help='Path to JSON output file.')
    parser.add_argument('--node-prefix', help='Node id prefix (e.g., ccr, exhibit-d).')
    parser.add_argument('--instrument-id', help='Instrument id.')
    parser.add_argument('--force', action='store_true', help='Allow non-content changes when output exists.')
    parser.add_argument('--base-doc-id', help='Base document id.')
    parser.add_argument('--title', help='Instrument title.')
    parser.add_argument('--instrument-kind', help='Instrument kind (declaration, amendment, exhibit, etc.).')
    parser.add_argument('--doc-type', help='Document type.')
    parser.add_argument('--jurisdiction', help='Jurisdiction.')
    parser.add_argument('--recorded-at', help='Recorded date (YYYY-MM-DD).')
    parser.add_argument('--effective-at', help='Effective date (YYYY-MM-DD).')
    parser.add_argument('--recording-county', help='Recording county.')
    parser.add_argument('--recording-state', help='Recording state.')
    parser.add_argument('--recording-book', help='Recording book.')
    parser.add_argument('--recording-page', help='Recording page.')
    args = parser.parse_args()
    md_path = Path(args.source)
    out_path = Path(args.output)
    text = md_path.read_text(encoding='utf-8')
    meta, body = extract_header(text)
    if out_path.exists():
        existing = json.loads(out_path.read_text(encoding='utf-8'))
        node_prefix = args.node_prefix or meta.get('node_prefix') or infer_node_prefix(existing)
        if not node_prefix:
            raise SystemExit('Could not infer node prefix from existing JSON; pass --node-prefix or add node_prefix in header.')
        included_in_instrument_id = (
            existing.get('instrument', {}).get('id')
            or args.instrument_id
            or meta.get('instrument_id')
        )
        parsed = parse_text(
            body,
            node_prefix=node_prefix,
            included_in_instrument_id=included_in_instrument_id,
        )
        updated = dict(existing)
        updated['content'] = parsed['content']
        if 'incorporations' in parsed:
            updated['incorporations'] = parsed['incorporations']
        if not args.force and strip_content(updated) != strip_content(existing):
            raise SystemExit('Refusing to write: non-content fields changed in content-replacement mode. Use --force to override.')
        with tempfile.NamedTemporaryFile(
            'w',
            encoding='utf-8',
            dir=str(out_path.parent),
            delete=False,
            prefix=f".{out_path.name}.",
            suffix=".tmp",
        ) as tmp_file:
            tmp_path = Path(tmp_file.name)
            tmp_file.write(json.dumps(updated, indent=2))
        tmp_path.replace(out_path)
        return

    node_prefix = args.node_prefix or meta.get('node_prefix')
    if not node_prefix:
        raise SystemExit('Missing node prefix; pass --node-prefix or add node_prefix in header.')
    instrument = build_instrument(meta, args)
    data = parse_text(
        body,
        node_prefix=node_prefix,
        included_in_instrument_id=instrument['id'],
    )
    data['instrument'] = instrument
    out_path.write_text(json.dumps(data, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
