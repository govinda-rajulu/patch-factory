#!/usr/bin/env python3
"""Small, bounded HTML selector adapter for the store pages."""
# W16o: stdlib replacement for pup (F-12)

import html
import json
import re
import sys
from html.parser import HTMLParser

MAX_INPUT = 16 * 1024 * 1024


class Raw:
    """A source fragment that pup preserves in plain HTML but excludes from text."""
    def __init__(self, value):
        self.value = value


class Node:
    def __init__(self, tag, attrs, raw_start, parent):
        self.tag = tag.lower()
        self.attrs = {name.lower(): (value if value is not None else "") for name, value in attrs}
        self.raw_start = raw_start
        self.raw_end = ""
        self.children = []
        self.parent = parent
        self.self_closing = raw_start.rstrip().endswith("/>")


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.root = Node("__root__", [], "", None)
        self.stack = [self.root]

    def _add(self, value):
        self.stack[-1].children.append(value)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.get_starttag_text() or ("<%s>" % tag), self.stack[-1])
        self._add(node)
        if tag.lower() not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._add(Node(tag, attrs, self.get_starttag_text() or ("<%s/>" % tag), self.stack[-1]))

    def handle_endtag(self, tag):
        wanted = tag.lower()
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == wanted:
                node = self.stack[i]
                node.raw_end = "</%s>" % tag
                del self.stack[i:]
                return

    def handle_data(self, data):
        self._add(data)

    def handle_entityref(self, name):
        self._add("&%s;" % name)

    def handle_charref(self, name):
        self._add("&#%s;" % name)

    def handle_comment(self, data):
        self._add(Raw("<!--%s-->" % data))

    def handle_decl(self, decl):
        self._add(Raw("<!%s>" % decl))

    def unknown_decl(self, data):
        self._add(Raw("<![%s]>" % data))

    def handle_pi(self, data):
        self._add(Raw("<?%s>" % data))


def parse_compound(token):
    """Parse the small CSS compound subset used by the build."""
    if not token or any(c in token for c in ">+~,*"):
        raise ValueError("unsupported selector component: %s" % token)
    m = re.match(r"^(?P<tag>[A-Za-z][\w:-]*)?", token)
    tag = m.group("tag") or "*"
    pos = m.end()
    classes = []
    ident = None
    attrs = []
    while pos < len(token):
        if token[pos] in ".#":
            marker = token[pos]
            part = re.match(r"[A-Za-z_][\w:-]*", token[pos + 1:])
            if not part:
                raise ValueError("bad selector component: %s" % token)
            value = part.group(0)
            if marker == ".":
                classes.append(value)
            elif ident is not None:
                raise ValueError("multiple ids are not supported: %s" % token)
            else:
                ident = value
            pos += 1 + len(value)
            continue
        if token[pos] == "[":
            end = token.find("]", pos + 1)
            if end < 0:
                raise ValueError("unterminated attribute filter: %s" % token)
            expr = token[pos + 1:end].strip()
            am = re.fullmatch(r"([A-Za-z_:][\w:.-]*)(?:\s*(=|\^=|\$=|\*=)\s*(?:'([^']*)'|\"([^\"]*)\"|([^\s]+)))?", expr)
            if not am:
                raise ValueError("bad attribute filter: %s" % token)
            value = am.group(3) if am.group(3) is not None else am.group(4)
            if value is None:
                value = am.group(5)
            attrs.append((am.group(1).lower(), am.group(2), value))
            pos = end + 1
            continue
        raise ValueError("unsupported selector component: %s" % token)
    return tag.lower(), ident, classes, attrs


def matches(node, compound):
    tag, ident, classes, attrs = compound
    if tag != "*" and node.tag != tag:
        return False
    if ident is not None and node.attrs.get("id") != ident:
        return False
    node_classes = set(node.attrs.get("class", "").split())
    if any(c not in node_classes for c in classes):
        return False
    for name, op, want in attrs:
        if name not in node.attrs:
            return False
        if op is None:
            continue
        got = node.attrs[name]
        if op == "=" and got != want:
            return False
        if op == "^=" and not got.startswith(want):
            return False
        if op == "$=" and not got.endswith(want):
            return False
        if op == "*=" and want not in got:
            return False
    return True


def select(root, selector):
    parts = selector.split()
    if not parts or any(not p for p in parts):
        raise ValueError("selector must not be empty")
    compounds = [parse_compound(p) for p in parts]
    all_nodes = []

    def walk(value):
        if isinstance(value, Node):
            all_nodes.append(value)
            for child in value.children:
                walk(child)

    walk(root)
    found = []
    for node in all_nodes:
        if not matches(node, compounds[-1]):
            continue
        ancestor = node.parent
        index = len(compounds) - 2
        while index >= 0:
            while ancestor is not None and not matches(ancestor, compounds[index]):
                ancestor = ancestor.parent
            if ancestor is None:
                break
            index -= 1
            ancestor = ancestor.parent
        if index < 0:
            found.append(node)
    return found


def text_of(node):
    bits = []

    def visit(value):
        if isinstance(value, Node):
            for child in value.children:
                visit(child)
        elif isinstance(value, str):
            bits.append(value)

    visit(node)
    return html.unescape("".join(bits)).strip()


def serialize(value):
    if isinstance(value, Raw):
        return value.value
    if not isinstance(value, Node):
        return value
    inside = "".join(serialize(child) for child in value.children)
    return value.raw_start + inside + (value.raw_end if value.raw_end else "")


def usage(message):
    print("html_select.py: %s" % message, file=sys.stderr)
    print("usage: html_select.py SELECTOR < HTML", file=sys.stderr)
    return 2


def main(argv):
    if len(argv) != 2:
        return usage("expected exactly one selector")
    selector = argv[1]
    operation = "plain"
    if selector.endswith(" json{}"):
        operation, selector = "json", selector[:-7].rstrip()
    elif selector.endswith(" text{}"):
        operation, selector = "text", selector[:-7].rstrip()
    else:
        match = re.fullmatch(r"(.+) attr\{([A-Za-z_:][\w:.-]*)\}", selector)
        if match:
            operation, selector, attr = "attr", match.group(1), match.group(2).lower()
        else:
            attr = None
    if not selector:
        return usage("selector is empty")
    try:
        compounds = [parse_compound(part) for part in selector.split()]
    except ValueError as exc:
        return usage(str(exc))
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
    except OSError as exc:
        print("html_select.py: cannot read HTML: %s" % exc, file=sys.stderr)
        return 1
    if len(raw) > MAX_INPUT:
        print("html_select.py: input exceeds %d bytes" % MAX_INPUT, file=sys.stderr)
        return 1
    try:
        parser = Document()
        parser.feed(raw.decode("utf-8", "replace"))
        parser.close()
        nodes = select(parser.root, selector)
    except (UnicodeError, ValueError) as exc:
        return usage(str(exc))
    if operation == "json":
        rows = []
        for node in nodes:
            row = {"text": text_of(node)}
            if "href" in node.attrs:
                row["href"] = node.attrs["href"]
            rows.append(row)
        print(json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
    elif operation == "text":
        for node in nodes:
            print(text_of(node))
    elif operation == "attr":
        for node in nodes:
            if attr in node.attrs:
                print(node.attrs[attr])
    else:
        for node in nodes:
            print(serialize(node))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
