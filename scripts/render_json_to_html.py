#!/usr/bin/env python3
import json
from pathlib import Path
import html


def render(json_path: Path, out_path: Path):
    data = json.loads(json_path.read_text(encoding='utf-8'))
    content = data['content']
    node_map = {n['id']: n for n in content['nodes']}

    def render_label(label):
        return f"<span class=\"label\">{html.escape(label)}</span> "

    def render_table(node):
        parts = []
        label = node.get('label')
        if label:
            parts.append(f"<div class=\"table-label\">{html.escape(label)}</div>")
        parts.append("<table>")
        cols = node.get('columns')
        if cols:
            parts.append("<thead><tr>")
            for col in cols:
                parts.append(f"<th>{html.escape(col)}</th>")
            parts.append("</tr></thead>")
        rows = node.get('rows', [])
        if rows:
            parts.append("<tbody>")
            for row in rows:
                parts.append("<tr>")
                for cell in row:
                    parts.append(f"<td>{html.escape(cell)}</td>")
                parts.append("</tr>")
            parts.append("</tbody>")
        parts.append("</table>")
        return "\n".join(parts)

    def render_node(node_id, depth=1, parent_type=None):
        node = node_map[node_id]
        t = node['type']
        parts = []
        meta = node.get('meta', {})
        note = meta.get('note') or meta.get('notes')
        if note:
            parts.append(f"<div class=\"meta-note\">{html.escape(note)}</div>")
        if t == 'heading':
            parts.append(f"<h1>{html.escape(node.get('text', ''))}</h1>")
        elif t in ('article', 'section', 'subsection', 'exhibit'):
            label = node.get('label')
            title = node.get('title')
            tag = 'h2' if depth == 1 else 'h3' if depth == 2 else 'h4'
            if t == 'exhibit':
                parts.append("<hr />")
                if label:
                    parts.append(f"<{tag}>{html.escape(label)}</{tag}>")
                if title:
                    higher_tag = 'h2' if tag == 'h3' else 'h3' if tag == 'h4' else 'h2'
                    parts.append(f"<{higher_tag}>{html.escape(title)}</{higher_tag}>")
            else:
                heading_text = " ".join(s for s in [label, title] if s)
                if heading_text:
                    parts.append(f"<{tag}>{html.escape(heading_text)}</{tag}>")
        elif t == 'paragraph':
            label = node.get('label')
            text = html.escape(node.get('text', ''))
            indent = node.get('meta', {}).get('indent_level')
            style = f" style=\"margin-left:{indent*1.5}em\"" if isinstance(indent, int) and indent > 0 else ""
            if label:
                parts.append(f"<p{style}>{render_label(label)}{text}</p>")
            else:
                parts.append(f"<p{style}>{text}</p>")
        elif t == 'list':
            parts.append("<ul>")
            for child in node.get('children', []):
                parts.append(render_node(child['ref'], depth, parent_type='list'))
            parts.append("</ul>")
        elif t == 'list_item':
            label = node.get('label')
            title = node.get('title')
            text = html.escape(node.get('text', ''))
            indent = node.get('meta', {}).get('indent_level')
            style = f" style=\"margin-left:{indent*1.5}em\"" if isinstance(indent, int) and indent > 0 else ""
            class_attr = " class=\"list-item-labeled\"" if label else ""
            inner = []
            if label:
                inner.append(render_label(label))
            if title:
                inner.append(f"<span class=\"list-item-title\">{html.escape(title)}</span> ")
            if text:
                inner.append(text)
            for child in node.get('children', []):
                inner.append(render_node(child['ref'], depth, parent_type='list_item'))
            parts.append(f"<li{class_attr}{style}>{''.join(inner)}</li>")
        elif t == 'table':
            parts.append(render_table(node))

        if t not in ('list', 'list_item'):
            for child in node.get('children', []):
                parts.append(render_node(child['ref'], depth + (1 if t in ('article', 'section', 'subsection', 'exhibit') else 0), parent_type=t))

        rendered = "\n".join(parts)
        if parent_type == 'list_item' and t in ('article', 'section', 'subsection', 'exhibit'):
            return f"<div class=\"list-item-child\">{rendered}</div>"
        return rendered

    root_id = content['root_ref']
    body_parts = []
    for child in node_map[root_id].get('children', []):
        body_parts.append(render_node(child['ref'], 1))

    html_doc = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(data['instrument'].get('title','Document'))}</title>
  <style>
    body {{ font-family: Georgia, 'Times New Roman', serif; line-height: 1.5; padding: 24px; max-width: 900px; margin: 0 auto; }}
    h1 {{ font-size: 24px; margin-top: 24px; }}
    h2 {{ font-size: 20px; margin-top: 24px; }}
    h3 {{ font-size: 18px; margin-top: 20px; }}
    h4 {{ font-size: 16px; margin-top: 18px; }}
    p {{ margin: 10px 0; }}
    .label {{ font-weight: bold; }}
    ul {{ margin: 10px 0 10px 24px; padding-left: 18px; }}
    li {{ margin: 6px 0; }}
    li.list-item-labeled {{ list-style: none; padding-left: 0; }}
    li.list-item-labeled::marker {{ content: ''; }}
    .list-item-title {{ font-weight: bold; }}
    .list-item-child {{ margin-left: 1.5em; }}
    .list-item-child > h2,
    .list-item-child > h3,
    .list-item-child > h4 {{ margin-top: 10px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
    th, td {{ border: 1px solid #aaa; padding: 6px 8px; text-align: left; vertical-align: top; }}
    .table-label {{ font-weight: bold; margin-top: 14px; }}
    .meta-note {{ background: #f2f2f2; color: #444; margin: 8px 0 10px; padding: 8px 10px; border-left: 4px solid #bbb; }}
  </style>
</head>
<body>
{''.join(body_parts)}
</body>
</html>
"""

    out_path.write_text(html_doc, encoding='utf-8')


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Render instrument JSON to HTML.')
    parser.add_argument('source', help='Path to JSON source file.')
    parser.add_argument('output', help='Path to HTML output file.')
    args = parser.parse_args()
    json_path = Path(args.source)
    out_path = Path(args.output)
    render(json_path, out_path)


if __name__ == '__main__':
    main()
