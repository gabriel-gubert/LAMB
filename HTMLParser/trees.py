import numpy as np
import pandas as pd
import re
import os
from urllib.parse import urlparse
from tree_sitter import Language
import tree_sitter_html as tshtml


class BaseTree:
    ''' Wrapper for a Tree-sitter Tree. '''

    _LANGUAGE = {
        'html': tshtml.language,
    }

    def __init__(self, tstree, filepath: str, language: str, encoding: str = 'utf-8'):
        self.tstree = tstree
        self.root_node = tstree.root_node
        self.filepath = filepath
        self.language = language
        self.encoding = encoding


    def types(self) -> list:
        def _get_type(node):
            type = []

            type.append(node.type)

            for i in range(node.child_count):
                child = node.child(i)

                type.extend(_get_type(child))

            return type

        return pd.DataFrame(_get_type(self.root_node)).drop_duplicates()[0].tolist()


    def match(self, query: str):
        LANGUAGE = Language(__class__._LANGUAGE[self.language]())
        matches = LANGUAGE.query(query).matches(self.root_node)

        return matches


    def capture(self, query: str):
        LANGUAGE = Language(__class__._LANGUAGE[self.language]())
        captures = LANGUAGE.query(query).captures(self.root_node)

        return captures


    def plot(self, path: str, width: int, height: int, root = None, max_depth: int = None):
        def _span(node):
            if node.child_count == 0:
                return 1

            span = 0

            for i in range(node.child_count):
                child = node.child(i)
                span += _span(child)
            
            return max(span, node.child_count)

        def _plot(node, x, y, node_width, node_height, x_margin, y_margin, canvas, max_depth):
            if max_depth is not None:
                if max_depth < 1:
                    return

            if x + node_width + x_margin >= canvas.shape[1] or y + node_height + y_margin >= canvas.shape[0] :
                return

            canvas[y, x + 1:x + node_width] = '-'
            canvas[y + node_height - 1, x + 1:x + node_width] = '-'
            canvas[y + 1:y + node_height, x] = '|'
            canvas[y + 1:y + node_height, x + node_width] = '|'
            canvas[y][x], canvas[y][x + node_width], canvas[y + node_height - 1][x + node_width], canvas[y + node_height - 1][x] = '+', '+', '+', '+'

            _type = node.type

            # if _type == 'tag_name':
            #     _type += f": {node.text.decode(self.encoding.lower())}"

            for i in range(len(_type)):
                canvas[y + int(node_height / 2), x + int((node_width - len(_type)) / 2) + i] = _type[i]

            s = 0

            for i in range(node.child_count):
                if i > 0:
                    s += (_span(node.child(i - 1)) - 1) * (node_width + 2)

                child = node.child(i)

                _plot(child, x + (node_width + x_margin) * i + s, y + node_height + y_margin, node_width, node_height, x_margin, y_margin, canvas, max_depth - 1 if max_depth else None)
    
            canvas[y + node_height + 1, x + int(node_width / 2):x + int(node_width / 2) + (node.child_count - 1) * (node_width + 2) + s + 1] = '-' if node.child_count > 0 else ' '
            canvas[y - 1, x + int(node_width / 2)] = '|' if node.parent else ' '
            canvas[y + node_height, x + int(node_width / 2)] = '|' if node.child_count > 0 else ' '

        canvas = [[' ' for _ in range(width)] for _ in range(height)]
        canvas = np.array(canvas)

        types = self.types()

        node_width = 0

        for t in types:
            if len(t) > node_width:
                node_width = len(t)

        node_width += 2
        node_height = 3
        x_margin = 2
        y_margin = 3

        _plot(self.root_node if root is None else root, 0, 0, node_width, node_height, x_margin, y_margin, canvas, max_depth)

        file = open(path, 'w')

        if max_depth is None:
            for i in range(height):
                file.write(f'{"".join(canvas[i])}\n')

            return

        for i in range(max_depth * (node_height + 3) - 3):
            file.write(f'{"".join(canvas[i])}\n')


    def source_files(self) -> list:
        def _get_source_file(node):
            source_files = []

            if node.type in self.__class__._SYNTAX['source_file']:
                source_files.append(node.text.decode(self.encoding.lower()))

            for i in range(node.child_count):
                child = node.child(i)

                source_files.extend(_get_source_file(child))

            return source_files

        return _get_source_file(self.root_node)


class HTMLTree(BaseTree):
    ''' Wrapper for a HTML Tree-sitter Tree. '''

    def __init__(self, tstree, filepath: str, language: str, encoding = 'utf-8'):
        super().__init__(tstree, filepath, language, encoding)


    def is_tag(self, node, tag: str) -> bool:
        if node.type == 'tag_name':
            return node.text.decode(self.encoding.lower()) == tag

        for i in range(node.child_count):
            child = node.child(i)

            if child.type == 'element':
                continue

            if self.is_tag(child, tag):
                return True

        return False


    def text_match(self, node, pattern: str) -> bool:
        if node.type in ['raw_text', 'text']:
            return re.search(pattern, node.text.decode(self.encoding.lower())) is not None

        for i in range(node.child_count):
            child = node.child(i)

            if self.text_match(child, pattern):
                return True

        return False


    def attribute_match(self, node, pattern: str) -> bool:
        if node.type in ['attribute_name']:
            return re.search(pattern, node.text.decode(self.encoding.lower())) is not None

        for i in range(node.child_count):
            child = node.child(i)

            if child.type == 'element':
                continue

            if self.attribute_match(child, pattern):
                return True

        return False


    def get_by_tag(self, tag: str, root = None, recursive: bool = True, max_depth: int = None, exceptions: list = []) -> list:
        def _get_by_tag(tag, node, recursive, max_depth, exceptions):
            elements = []

            if node.type == 'element' and self.is_tag(node, tag):
                elements.append(node)

            if recursive:
                for i in range(node.child_count):
                    child = node.child(i)

                    if any([self.is_tag(child, exception) for exception in exceptions]):
                        continue

                    if max_depth is None:
                        elements.extend(_get_by_tag(tag, child, recursive, None, exceptions))

                        continue

                    if max_depth <= 0:
                        break

                    if child.type == 'element':
                        elements.extend(_get_by_tag(tag, child, recursive, max_depth - 1, exceptions))

                        continue

                    elements.extend(_get_by_tag(tag, child, recursive, max_depth, exceptions))

            return elements

        if root is None:
            return _get_by_tag(tag, self.root_node, recursive, max_depth, exceptions)

        return _get_by_tag(tag, root, recursive, max_depth, exceptions)


    def get_by_tags(self, tags: list[str], root = None, recursive: bool = True, max_depth: int = None, exceptions: list = []):
        def _get_by_tags(tags, node, recursive, max_depth, exceptions):
            elements = []

            if node.type == 'element' and any([self.is_tag(node, tag) for tag in tags]):
                elements.append(node)

            if recursive:
                for i in range(node.child_count):
                    child = node.child(i)

                    if any([self.is_tag(child, exception) for exception in exceptions]):
                        continue

                    if max_depth is None:
                        elements.extend(_get_by_tags(tags, child, recursive, None, exceptions))

                        continue

                    if max_depth <= 0:
                        break

                    if child.type == 'element':
                        elements.extend(_get_by_tags(tags, child, recursive, max_depth - 1, exceptions))

                        continue

                    elements.extend(_get_by_tags(tags, child, recursive, max_depth, exceptions))

            return elements

        if root is None:
            return _get_by_tags(tags, self.root_node, recursive, max_depth, exceptions)

        return _get_by_tags(tags, root, recursive, max_depth, exceptions)


    def get_by_text(self, pattern: str, root = None, recursive: bool = True, max_depth: int = None, exceptions: list = []) -> list:
        def _get_by_text(pattern, node, recursive, max_depth, exceptions):
            elements = []

            if node.type == 'element' and self.text_match(node, pattern):
                elements.append(node)

            if recursive:
                for i in range(node.child_count):
                    child = node.child(i)

                    if any([self.is_tag(child, exception) for exception in exceptions]):
                        continue

                    if max_depth is None:
                        elements.extend(_get_by_text(pattern, child, recursive, None, exceptions))

                        continue

                    if max_depth <= 0:
                        break

                    if child.type == 'element':
                        elements.extend(_get_by_text(pattern, child, recursive, max_depth - 1, exceptions))

                        continue

                    elements.extend(_get_by_text(pattern, child, recursive, max_depth, exceptions))

            return elements

        if root is None:
            return _get_by_text(pattern, self.root_node, recursive, max_depth, exceptions)

        return _get_by_text(pattern, root, recursive, max_depth, exceptions)


    def get_by_attribute(self, root, attribute: str, recursive: bool = True, max_depth: int = None, exceptions: list = []) -> list:
        def _get_by_attribute(node, pattern, recursive, max_depth, exceptions):
            elements = []

            if node.type == 'element' and self.attribute_match(node, pattern):
                elements.append(node)

            if recursive:
                for i in range(node.child_count):
                    child = node.child(i)

                    if any([self.is_tag(child, exception) for exception in exceptions]):
                        continue

                    if max_depth is None:
                        elements.extend(_get_by_attribute(child, pattern, recursive, None, exceptions))

                        continue

                    if max_depth <= 0:
                        break

                    if child.type == 'element':
                        elements.extend(_get_by_attribute(child, pattern, recursive, max_depth - 1, exceptions))

                        continue

                    elements.extend(_get_by_attribute(child, pattern, recursive, max_depth, exceptions))

            return elements
        return _get_by_attribute(root, attribute, recursive, max_depth, exceptions)


    def get_texts(self, root, recursive: bool = True, max_depth: int = None, exceptions: list = [], follow_link: bool = False, link_max_depth: int = None, visited_paths: list = None, formatted: bool = False) -> list:
        def is_absolute(url):
            return bool(urlparse(url).scheme) and bool(urlparse(url).netloc)

        def _get_text(node, recursive, max_depth, exceptions, formatted) -> list:
            texts = []

            if formatted:
                if self.is_tag(node, 'table'):
                    return [self.format_table(self.get_table_as_json(node))]
                elif self.is_tag(node, 'code'):
                    return [self.format_code(' '.join(self.get_texts(node)))]
                elif self.is_tag(node, 'pre'):
                    return [self.format_pre(self.get_raw_text(node))]
                elif self.is_tag(node, 'ul') or self.is_tag(node, 'ol'):
                    return [self.format_ul(self.get_ul_as_json(node))]
                elif self.is_tag(node, 'b') or self.is_tag(node, 'strong'):
                    return [f"**{' '.join(self.get_texts(node))}**"]
                elif self.is_tag(node, 'i') or self.is_tag(node, 'em'):
                    return [f"*{' '.join(self.get_texts(node))}*"]
                elif self.is_tag(node, 's') or self.is_tag(node, 'del'):
                    return [f"~~{' '.join(self.get_texts(node))}~~"]
                elif self.is_tag(node, 'blockquote'):
                    return [f"> {' '.join(self.get_texts(node))}"]
                elif self.is_tag(node, 'hr'):
                    return ["\n---\n"]
                elif self.is_tag(node, 'h1'):
                    return [f"# {' '.join(self.get_texts(node))}"]
                elif self.is_tag(node, 'h2'):
                    return [f"## {' '.join(self.get_texts(node))}"]
                elif self.is_tag(node, 'h3'):
                    return [f"### {' '.join(self.get_texts(node))}"]
                elif self.is_tag(node, 'h4'):
                    return [f"#### {' '.join(self.get_texts(node))}"]
                elif self.is_tag(node, 'h5'):
                    return [f"##### {' '.join(self.get_texts(node))}"]
                elif self.is_tag(node, 'h6'):
                    return [f"###### {' '.join(self.get_texts(node))}"]

            if node.type in ['raw_text', 'text']:
                texts.append(node.text.decode(self.encoding.lower()))
            elif node.type == 'entity':
                try:
                    texts.append(HTMLTree.HTML_ENTITIES[node.text.decode(self.encoding.lower())])
                except:
                    print(f'Unrecognized HTML Entity \"{node.text.decode(self.encoding.lower())}\".')

            if recursive:
                for i in range(node.child_count):
                    child = node.child(i)

                    if any([self.is_tag(child, exception) for exception in exceptions]):
                        continue

                    if max_depth is None:
                        if child.type == 'element':
                            if any([self.is_tag(child, tag) for tag in HTMLTree.BLOCK_TAGS]) or self.is_tag(child, 'br'):
                                texts.append('\n')

                        texts.extend(_get_text(child, recursive, None, exceptions, formatted))

                        continue

                    if max_depth <= 0:
                        break

                    if child.type == 'element':
                        if any([self.is_tag(child, tag) for tag in HTMLTree.BLOCK_TAGS]) or self.is_tag(child, 'br'):
                            texts.append('\n')

                        texts.extend(_get_text(child, recursive, max_depth - 1, exceptions, formatted))

                        continue

                    texts.extend(_get_text(child, recursive, max_depth, exceptions, formatted))

            return texts

        texts = _get_text(root, recursive, max_depth, exceptions, formatted)

        i = 0
        while i < len(texts) - 1:
            if texts[i] == '\n' or texts[i] == '\r' or texts[i] == '\t':
                texts[i + 1] = texts[i] + texts[i + 1]
                texts.pop(i)

            i += 1

        if follow_link:
            if link_max_depth is None or link_max_depth > 0:
                if visited_paths is None:
                    visited_paths = []

                visited_paths.append(os.path.abspath(self.filepath))

                links = self.get_by_tag('a', root, recursive, max_depth, exceptions)

                for link in links:
                    attributes = self.get_attributes(link)

                    for attribute in attributes:
                        attribute_name, attribute_value = str.split(attribute, '=')

                        if attribute_name == 'href':
                            attribute_value = attribute_value.replace('"', '')

                            if is_absolute(attribute_value) or attribute_value[0] == '#' or attribute_value[0] == '/':
                                break

                            filepath = os.path.abspath(
                                os.path.join(
                                    os.path.dirname(os.path.abspath(self.filepath)), 
                                    attribute_value
                                )
                            )

                            if os.path.exists(filepath):
                                if filepath not in visited_paths:
                                    from .parser import parse

                                    html_tree = parse(filepath, encoding=self.encoding.lower())

                                    text = html_tree.get_texts(html_tree.root_node, exceptions = ['head'], follow_link = follow_link, link_max_depth = link_max_depth - 1, visited_paths = visited_paths, formatted = True)

                                    texts.extend(text)

        return texts


    def get_raw_text(self, root = None, exceptions: list = []) -> str:
        node = root

        if node is None:
            node = self.root_node

        text = node.text.decode(self.encoding)

        for exception in exceptions:
            elements = self.get_by_tag(exception, node)

            for element in elements:
                text = text.replace(element.text.decode(self.encoding), '')

        while True:
            match = re.search('<[\s\S]*?>', text)

            if match is None:
                break

            text = text[:match.start()] + text[match.end():]

        for key in HTMLTree.HTML_ENTITIES.keys():
            text = text.replace(key, HTMLTree.HTML_ENTITIES[key])

        return text


    def get_attributes(self, root, recursive: bool = True, max_depth: int = None, exceptions: list = []) -> list:
        def _get_attribute(node, recursive, max_depth, exceptions):
            attributes = []

            if node.type == 'attribute':
                attributes.append(node.text.decode(self.encoding.lower()))

            if recursive:
                for i in range(node.child_count):
                    child = node.child(i)

                    if any([self.is_tag(child, exception) for exception in exceptions]):
                        continue

                    if max_depth is None:
                        attributes.extend(_get_attribute(child, recursive, None, exceptions))

                        continue

                    if max_depth <= 0:
                        break

                    if child.type == 'element':
                        attributes.extend(_get_attribute(child, recursive, max_depth - 1, exceptions))

                        continue

                    attributes.extend(_get_attribute(child, recursive, max_depth, exceptions))

            return attributes
        return _get_attribute(root, recursive, max_depth, exceptions)


    def get_table_as_json(self, node, recursive: bool = True, raw_text: bool = False, follow_link: bool = False, link_max_depth: int = None):
        ''' Get a HTML Table Node as a JSON Object. The table (and possibly its nested tables) should be of the form(s):

            1. w/ <thead>, <tbody> and <tfoot>

                <table>
                    <thead>
                        <tr>
                            <th>|<td> Header 1 </th>|</td>
                            <th>|<td> Header 2 </th>|</td>
                            ...
                            <th>|<td> Header N </th>|</td>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td> Column 1 </td>
                            <td> Column 2 </td>
                            ...
                            <td> Column N </td>
                        </tr>
                        ...
                    </tbody>
                    <tfoot>
                        <tr>
                            <td> Column 1 </td>
                            <td> Column 2 </td>
                            ...
                            <td> Column N </td>
                        </tr>
                        ...
                    </tfoot>
                </table>

            2. w/o <thead>, <tbody> and <tfoot>

                <table> 
                    <tr>
                        <th>|<td> Header 1 </th>|</td>
                        <th>|<td> Header 2 </th>|</td>
                        ...
                        <th>|<td> Header N </th>|</td>
                    </tr>
                    <tr>
                        <td> Column 1 </td>
                        <td> Column 2 </td>
                        ...
                        <td> Column N </td>
                    </tr>
                    ...
                </table>

            Keyword arguments:
            raw_text -- Whether or not to fill Table Cells with RAW HTML Text w/o Element Tags. (default False)
        '''

        def get_height(table: dict):
            height = 0

            for key in table.keys():
                length = len(table[key])

                if length > height:
                    height = length

            return height


        def fill(table: dict, value = None):
            height = get_height(table)

            for key in table.keys():
                length = len(table[key])

                if length < height:
                    if value is None:
                        table[key].extend([table[key][-1] for _ in range(height - length)])

                        continue

                    table[key].extend([value for _ in range(height - length)])

            return table

        table = {}

        if self.is_tag(node, 'table'):
            rows = self.get_by_tag('tr', node, max_depth = 1)
            
            if len(rows) == 0:
                rows = self.get_by_tag('tr', node, max_depth = 2)

                if len(rows) == 0:
                    return {}

            headers_colspan = []
            headers = self.get_by_tag('th', rows[0], max_depth = 1)

            if len(headers) == 0:
                headers = self.get_by_tag('td', rows[0], max_depth = 1)

                if len(headers) == 0:
                    return {}

            for i in range(len(headers)):
                colspan = 1
                attributes = self.get_attributes(headers[i])

                for attribute in attributes:
                    attribute_name, attribute_value = str.split(attribute, '=')

                    if attribute_name == 'colspan':
                        colspan = int(attribute_value.replace('"', ''))

                        break

                headers_colspan.append(colspan)
                text = self.get_texts(headers[i], formatted = True)
                text = ' '.join(text).replace(' \n ', '\n').replace('\t', '') or f'Column {i}'
                text = self.removetrailing(text, '\n')
                text = self.removetrailing(text, ' ')

                j = 2
                while True:
                    if text in table.keys():
                        text = f'{text} ({j})'
                        j += 1

                        continue

                    table[text] = []

                    break

            headers = list(table.keys())

            for row in rows[1:]:
                for key in table.keys():
                    table[key].append('')

                columns_colspan = []
                columns_colspan.extend(headers_colspan)
                columns = self.get_by_tag('td', row, max_depth = 1)

                for column in columns:
                    colspan = 1

                    attributes = self.get_attributes(column)

                    for attribute in attributes:
                        attribute_name, attribute_value = str.split(attribute, '=')

                        if attribute_name == 'colspan':
                            colspan = int(attribute_value.replace('"', ''))

                            break

                    columns_colspan_ = []
                    columns_colspan_.extend(columns_colspan)

                    for i in range(len(columns_colspan)):
                        if columns_colspan_[i] == 0:

                            continue

                        columns_colspan_[i] = max(columns_colspan_[i] - colspan, 0)
                        label = headers[i]

                        break

                    if recursive:
                        nested_tables = self.get_by_tag('table', column, max_depth = 1)
                        height = get_height(table)

                        for nested_table in nested_tables:
                            nested_table_as_json = self.get_table_as_json(nested_table, follow_link = follow_link, link_max_depth = link_max_depth)

                            for key in nested_table_as_json.keys():
                                if f'{label}/{key}' not in table.keys():
                                    table[f'{label}/{key}'] = ['' for _ in range(height - 1)]
                                    table[f'{label}/{key}'].extend(nested_table_as_json[key])

                                    continue

                                table[f'{label}/{key}'].pop()
                                table[f'{label}/{key}'].extend(nested_table_as_json[key])

                        if raw_text:
                            text = self.get_raw_text(column, exceptions = ['table', 'head'])
                        else:
                            text = self.get_texts(column, exceptions = ['table', 'head'], follow_link = follow_link, link_max_depth = link_max_depth, formatted = True)
                    else:
                        if raw_text:
                            text = self.get_raw_text(column, exceptions = ['head'])
                        else:
                            text = self.get_texts(column, exceptions = ['head'], follow_link = follow_link, link_max_depth = link_max_depth, formatted = True)

                    if not raw_text:
                        text = ' '.join(text)

                    for i in range(len(columns_colspan)):
                        if columns_colspan[i] == 0:

                            continue

                        columns_colspan[i] = max(columns_colspan[i] - colspan, 0)
                        table[headers[i]][-1] += self.removetrailing(text, ' ')

                        break

                table = fill(table)

        table = fill(table, '')

        return table


    def get_ul_as_json(self, ul) -> dict:
        ul_as_json = {}

        if not any([self.is_tag(ul, 'ul'), self.is_tag(ul, 'ol')]):
            return {}

        elements = self.get_by_tags(['ul', 'ol', 'li'], ul, max_depth = 1)

        for i in range(1, len(elements)):
            element = elements[i]

            if self.is_tag(element, 'ul') or self.is_tag(element, 'ol'):
                ul_as_json.update({i: self.get_ul_as_json(element)})
            elif self.is_tag(element, 'li'):
                text = [self.removetrailing(' '.join(self.get_texts(element, formatted = True)), '\n')]
                _elements = self.get_by_tags(['ul', 'ol', 'li'], element, max_depth = 1)

                for _element in _elements[1:]:
                    _text = self.removetrailing(' '.join(self.get_texts(_element, formatted = True)), '\n')

                    for j in range(len(text)):
                        text[j] = text[j].split(_text)
                        text[j] = [(text[j][k], self.get_ul_as_json(_element)) for k in range(len(text[j]) - 1)]

                    text = [text[m][n][o] for m in range(len(text)) for n in range(len(text[m])) for o in range(len(text[m][n]))]

                ul_as_json.update({
                    i: text
                })

        return ul_as_json


    def format_table(self, table: dict) -> str:
        if not isinstance(table, dict) or not table:
            return ""

        headers = list(table.keys())

        try:
            num_rows = len(next(iter(table.values())))
        except (StopIteration, TypeError):
            num_rows = 0

        if not all(isinstance(v, list) and len(v) == num_rows for v in table.values()):
            return ""

        col_widths = {}
        header_height = 0

        for header in headers:
            lines = str(header).split('\n')
            col_widths[header] = max(len(line) for line in lines) if lines else 0
            header_height = max(header_height, len(lines))

            for value in table[header]:
                lines = str(value).split('\n')
                max_line_width = max(len(line) for line in lines) if lines else 0
                col_widths[header] = max(col_widths.get(header, 0), max_line_width)

        table_lines = []
        separator_str = "+-" + "-+-".join(["-" * col_widths[h] for h in headers]) + "-+"
        header_format = "| " + " | ".join([f"{{:<{col_widths[h]}}}" for h in headers]) + " |"
        row_format = "| " + " | ".join([f"{{:<{col_widths[h]}}}" for h in headers]) + " |"

        table_lines.append(separator_str)

        header_row_data_split = [str(header).split('\n') for header in headers]
        header_row_height = max(len(header_cell_lines) for header_cell_lines in header_row_data_split) if header_row_data_split else 1

        for j in range(header_row_height):
            header_sub_row_values = []

            for header_cell_lines in header_row_data_split:
                if j < len(header_cell_lines):
                    header_sub_row_values.append(header_cell_lines[j])
                else:
                    header_sub_row_values.append("")

            table_lines.append(header_format.format(*header_sub_row_values))

        table_lines.append(separator_str)

        for i in range(num_rows):
            row_data_split = [str(table[h][i]).split('\n') for h in headers]
            row_height = max(len(cell_lines) for cell_lines in row_data_split) if row_data_split else 1

            for j in range(row_height):
                sub_row_values = []

                for cell_lines in row_data_split:
                    if j < len(cell_lines):
                        sub_row_values.append(cell_lines[j])
                    else:
                        sub_row_values.append("")
                
                table_lines.append(row_format.format(*sub_row_values))

            if i < num_rows - 1:
                table_lines.append(separator_str)

        if num_rows > 0:
            table_lines.append(separator_str)

        return "\n".join(table_lines)


    def format_code(self, code: str) -> str:
        return f"`{self.removetrailing(code, ' ')}`"



    def format_pre(self, pre: str) -> str:
        aux = self.removetrailing(self.removetrailing(pre, ' '), '\n')

        return f"```\n{aux}\n```"


    def format_ul(self, ul: dict) -> str:
        formatted_ul = ''

        for key in ul.keys():
            if isinstance(ul[key], str):
                formatted_ul += '\t- ' + ul[key].replace('\t', '').replace('\n', '\n\t') + '\n'
            elif isinstance(ul[key], dict):
                formatted_ul += self.format_ul(ul[key]).replace('\t', '\t\t')
            elif isinstance(ul[key], list):
                for i in ul[key]:
                    if isinstance(i, str):
                        formatted_ul += '\t- ' + i.replace('\t', '').replace('\n', '\n\t') + '\n'
                    elif isinstance(i, dict):
                        formatted_ul += self.format_ul(i).replace('\t', '\t\t')

        return formatted_ul

    def removetrailing(self, src: str, value: str):
        _src = src[:]

        while True:
            aux = _src.removeprefix(value)

            if aux == _src:
                break

            _src = aux

        while True:
            aux = _src.removesuffix(value)

            if aux == _src:
                break

            _src = aux

        return _src


    BLOCK_TAGS = {'address', 'article', 'aside', 'footer', 'header', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hgroup', 'main', 'nav', 'section', 'blockquote', 'dd', 'div', 'dl', 'dt', 'figure', 'figcaption', 'hr', 'li', 'ol', 'p', 'pre', 'ul', 'form', 'fieldset', 'legend', 'output', 'table', 'caption', 'thead', 'tbody', 'tfoot', 'tr', 'audio', 'canvas', 'video', 'details', 'dialog', 'summary'}
    INLINE_TAGS = {'a', 'abbr', 'b', 'bdi', 'bdo', 'br', 'cite', 'code', 'data', 'dfn', 'em', 'i', 'kbd', 'mark', 'q', 'rp', 'rt', 'ruby', 's', 'samp', 'small', 'span', 'strong', 'sub', 'sup', 'time', 'u', 'var', 'wbr', 'audio', 'canvas', 'embed', 'iframe', 'img', 'object', 'picture', 'svg', 'video', 'button', 'input', 'label', 'meter', 'output', 'progress', 'select', 'textarea', 'area', 'map', 'script', 'slot', 'template'}
    HTML_ENTITIES_ASCII = {'&#32;': ' ', '&#33;': '!', '&quot;': '"', '&#34;': '"', '&#35;': '#', '&#36;': '$', '&#37;': '%', '&amp;': '&', '&#38;': '&', '&#39;': "'", '&#40;': '(', '&#41;': ')', '&#42;': '*', '&#43;': '+', '&#44;': ',', '&#45;': '-', '&#46;': '.', '&#47;': '/', '&#48;': '0', '&#49;': '1', '&#50;': '2', '&#51;': '3', '&#52;': '4', '&#53;': '5', '&#54;': '6', '&#55;': '7', '&#56;': '8', '&#57;': '9', '&#58;': ':', '&#59;': ';', '&lt;': '<', '&#60;': '<', '&#61;': '=', '&gt;': '>', '&#62;': '>','&#63;': '?','&#64;': '@', '&#65;': 'A', '&#66;': 'B', '&#67;': 'C', '&#68;': 'D', '&#69;': 'E', '&#70;': 'F', '&#71;': 'G', '&#72;': 'H', '&#73;': 'I', '&#74;': 'J', '&#75;': 'K', '&#76;': 'L', '&#77;': 'M', '&#78;': 'N', '&#79;': 'O', '&#80;': 'P', '&#81;': 'Q', '&#82;': 'R', '&#83;': 'S', '&#84;': 'T', '&#85;': 'U', '&#86;': 'V', '&#87;': 'W', '&#88;': 'X', '&#89;': 'Y', '&#90;': 'Z', '&#91;': '[', '&#92;': '\\', '&#93;': ']', '&#94;': '^', '&#95;': '_', '&#96;': '`', '&#97;': 'a', '&#98;': 'b', '&#99;': 'c', '&#100;': 'd', '&#101;': 'e', '&#102;': 'f', '&#103;': 'g', '&#104;': 'h', '&#105;': 'i', '&#106;': 'j', '&#107;': 'k', '&#108;': 'l', '&#109;': 'm', '&#110;': 'n', '&#111;': 'o', '&#112;': 'p', '&#113;': 'q', '&#114;': 'r', '&#115;': 's', '&#116;': 't', '&#117;': 'u', '&#118;': 'v', '&#119;': 'w', '&#120;': 'x', '&#121;': 'y', '&#122;': 'z', '&#123;': '{', '&#124;': '|', '&#125;': '}', '&#126;': '~'}
    HTML_ENTITIES_ISO_8859_1_CHARACTERS = {'&#32;': ' ', '&#33;': '!', '&#34;': '"', '&#35;': '#', '&#36;': '$', '&#37;': '%', '&amp;': '&', '&#38;': '&', '&#39;': "'", '&#40;': '(', '&#41;': ')', '&#42;': '*', '&#43;': '+', '&#44;': ',', '&#45;': '-', '&#46;': '.', '&#47;': '/', '&#48;': '0', '&#49;': '1', '&#50;': '2', '&#51;': '3', '&#52;': '4', '&#53;': '5', '&#54;': '6', '&#55;': '7', '&#56;': '8', '&#57;': '9', '&#58;': ':', '&#59;': ';', '&lt;': '<', '&#60;': '<', '&#61;': '=', '&gt;': '>', '&#62;': '>', '&#63;': '?', '&#64;': '@', '&#65;': 'A', '&#66;': 'B', '&#67;': 'C', '&#68;': 'D', '&#69;': 'E', '&#70;': 'F', '&#71;': 'G', '&#72;': 'H', '&#73;': 'I', '&#74;': 'J', '&#75;': 'K', '&#76;': 'L', '&#77;': 'M', '&#78;': 'N', '&#79;': 'O', '&#80;': 'P', '&#81;': 'Q', '&#82;': 'R', '&#83;': 'S', '&#84;': 'T', '&#85;': 'U', '&#86;': 'V', '&#87;': 'W', '&#88;': 'X', '&#89;': 'Y', '&#90;': 'Z', '&#91;': '[', '&#92;': '\\', '&#93;': ']', '&#94;': '^', '&#95;': '_', '&#96;': '`', '&#97;': 'a', '&#98;': 'b', '&#99;': 'c', '&#100;': 'd', '&#101;': 'e', '&#102;': 'f', '&#103;': 'g', '&#104;': 'h', '&#105;': 'i', '&#106;': 'j', '&#107;': 'k', '&#108;': 'l', '&#109;': 'm', '&#110;': 'n', '&#111;': 'o', '&#112;': 'p', '&#113;': 'q', '&#114;': 'r', '&#115;': 's', '&#116;': 't', '&#117;': 'u', '&#118;': 'v', '&#119;': 'w', '&#120;': 'x', '&#121;': 'y', '&#122;': 'z', '&#123;': '{', '&#124;': '|', '&#125;': '}', '&#126;': '~'}    
    HTML_ENTITIES_ISO_8859_1_SYMBOLS = {'&#160;': '', '&nbsp;': '', '&#161;': '¡', '&iexcl;': '¡', '&#162;': '¢', '&cent;': '¢', '&#163;': '£', '&pound;': '£', '&#164;': '¤', '&curren;': '¤', '&#165;': '¥', '&yen;': '¥', '&#166;': '¦', '&brvbar;': '¦', '&#167;': '§', '&sect;': '§', '&#168;': '¨', '&uml;': '¨', '&#169;': '©', '&copy;': '©', '&#170;': 'ª', '&ordf;': 'ª', '&#171;': '«', '&laquo;': '«', '&#172;': '¬', '&not;': '¬', '&#173;': '\xad', '&shy;': '\xad', '&#174;': '®', '&reg;': '®', '&#175;': '¯', '&macr;': '¯', '&#176;': '°', '&deg;': '°', '&#177;': '±', '&plusmn;': '±', '&#178;': '²', '&sup2;': '²', '&#179;': '³', '&sup3;': '³', '&#180;': '´', '&acute;': '´', '&#181;': 'µ', '&micro;': 'µ', '&#182;': '¶', '&para;': '¶', '&#184;': '¸', '&cedil;': '¸', '&#185;': '¹', '&sup1;': '¹', '&#186;': 'º', '&ordm;': 'º', '&#187;': '»', '&raquo;': '»', '&#188;': '¼', '&frac14;': '¼', '&#189;': '½', '&frac12;': '½', '&#190;': '¾', '&frac34;': '¾', '&#191;': '¿', '&iquest;': '¿', '&#215;': '×', '&times;': '×', '&#247;': '÷', '&divide;': '÷'}
    HTML_ENTITIES_MATH_SYMBOLS = {'&#8704;': '∀', '&forall;': '∀', '&#8706;': '∂', '&part;': '∂', '&#8707;': '∃', '&exist;': '∃', '&#8709;': '∅', '&empty;': '∅', '&#8711;': '∇', '&nabla;': '∇', '&#8712;': '∈', '&isin;': '∈', '&#8713;': '∉', '&notin;': '∉', '&#8715;': '∋', '&ni;': '∋', '&#8719;': '∏', '&prod;': '∏', '&#8721;': '∑', '&sum;': '∑', '&#8722;': '−', '&minus;': '−', '&#8727;': '∗', '&lowast;': '∗', '&#8730;': '√', '&radic;': '√', '&#8733;': '∝', '&prop;': '∝', '&#8734;': '∞', '&infin;': '∞', '&#8736;': '∠', '&ang;': '∠', '&#8743;': '∧', '&and;': '∧', '&#8744;': '∨', '&or;': '∨', '&#8745;': '∩', '&cap;': '∩', '&#8746;': '∪', '&cup;': '∪', '&#8747;': '∫', '&int;': '∫', '&#8756;': '∴', '&there4;': '∴', '&#8764;': '∼', '&sim;': '∼', '&#8773;': '≅', '&cong;': '≅', '&#8776;': '≈', '&asymp;': '≈', '&#8800;': '≠', '&ne;': '≠', '&#8801;': '≡', '&equiv;': '≡', '&#8804;': '≤', '&le;': '≤', '&#8805;': '≥', '&ge;': '≥', '&#8834;': '⊂', '&sub;': '⊂', '&#8835;': '⊃', '&sup;': '⊃', '&#8836;': '⊄', '&nsub;': '⊄', '&#8838;': '⊆', '&sube;': '⊆', '&#8839;': '⊇', '&supe;': '⊇', '&#8853;': '⊕', '&oplus;': '⊕', '&#8855;': '⊗', '&otimes;': '⊗', '&#8869;': '⊥', '&perp;': '⊥', '&#8901;': '⋅', '&sdot;': '⋅'}
    HTML_ENTITIES_GREEK_LETTERS = {'&#913;': 'Α', '&Alpha;': 'Α', '&#914;': 'Β', '&Beta;': 'Β', '&#915;': 'Γ', '&Gamma;': 'Γ', '&#916;': 'Δ', '&Delta;': 'Δ', '&#917;': 'Ε', '&Epsilon;': 'Ε', '&#918;': 'Ζ', '&Zeta;': 'Ζ', '&#919;': 'Η', '&Eta;': 'Η', '&#920;': 'Θ', '&Theta;': 'Θ', '&#921;': 'Ι', '&Iota;': 'Ι', '&#922;': 'Κ', '&Kappa;': 'Κ', '&#923;': 'Λ', '&Lambda;': 'Λ', '&#924;': 'Μ', '&Mu;': 'Μ', '&#925;': 'Ν', '&Nu;': 'Ν', '&#926;': 'Ξ', '&Xi;': 'Ξ', '&#927;': 'Ο', '&Omicron;': 'Ο', '&#928;': 'Π', '&Pi;': 'Π', '&#929;': 'Ρ', '&Rho;': 'Ρ', '&#931;': 'Σ', '&Sigma;': 'Σ', '&#932;': 'Τ', '&Tau;': 'Τ', '&#933;': 'Υ', '&Upsilon;': 'Υ', '&#934;': 'Φ', '&Phi;': 'Φ', '&#935;': 'Χ', '&Chi;': 'Χ', '&#936;': 'Ψ', '&Psi;': 'Ψ', '&#937;': 'Ω', '&Omega;': 'Ω', '&#945;': 'α', '&alpha;': 'α', '&#946;': 'β', '&beta;': 'β', '&#947;': 'γ', '&gamma;': 'γ', '&#948;': 'δ', '&delta;': 'δ', '&#949;': 'ε', '&epsilon;': 'ε', '&#950;': 'ζ', '&zeta;': 'ζ', '&#951;': 'η', '&eta;': 'η', '&#952;': 'θ', '&theta;': 'θ', '&#953;': 'ι', '&iota;': 'ι', '&#954;': 'κ', '&kappa;': 'κ', '&#955;': 'λ', '&lambda;': 'λ', '&#956;': 'μ', '&mu;': 'μ', '&#957;': 'ν', '&nu;': 'ν', '&#958;': 'ξ', '&xi;': 'ξ', '&#959;': 'ο', '&omicron;': 'ο', '&#960;': 'π', '&pi;': 'π', '&#961;': 'ρ', '&rho;': 'ρ', '&#962;': 'ς', '&sigmaf;': 'ς', '&#963;': 'σ', '&sigma;': 'σ', '&#964;': 'τ', '&tau;': 'τ', '&#965;': 'υ', '&upsilon;': 'υ', '&#966;': 'φ', '&phi;': 'φ', '&#967;': 'χ', '&chi;': 'χ', '&#968;': 'ψ', '&psi;': 'ψ', '&#969;': 'ω', '&omega;': 'ω', '&#977;': 'ϑ', '&thetasym;': 'ϑ', '&#978;': 'ϒ', '&upsih;': 'ϒ', '&#982;': 'ϖ', '&piv;': 'ϖ'}
    HTML_ENTITIES_MISCELLANEOUS = {'&OElig;': 'Œ', '&#338;': 'Œ', '&oelig;': 'œ', '&#339;': 'œ', '&Scaron;': 'Š', '&#352;': 'Š', '&scaron;': 'š', '&#353;': 'š', '&Yuml;': 'Ÿ', '&#376;': 'Ÿ', '&fnof;': 'ƒ', '&#402;': 'ƒ', '&circ;': 'ˆ', '&#710;': 'ˆ', '&tilde;': '˜', '&#732;': '˜', '&ensp;': '\u2002', '&#8194;': '\u2002', '&emsp;': '\u2003', '&#8195;': '\u2003', '&thinsp;': '\u2009', '&#8201;': '\u2009', '&zwnj;': '\u200c', '&#8204;': '\u200c', '&zwj;': '\u200d', '&#8205;': '\u200d', '&lrm;': '\u200e', '&#8206;': '\u200e', '&rlm;': '\u200f', '&#8207;': '\u200f', '&ndash;': '–', '&#8211;': '–', '&mdash;': '—', '&#8212;': '—', '&lsquo;': '‘', '&#8216;': '‘', '&rsquo;': '’', '&#8217;': '’', '&sbquo;': '‚', '&#8218;': '‚', '&ldquo;': '“', '&#8220;': '“', '&rdquo;': '”', '&#8221;': '”', '&bdquo;': '„', '&#8222;': '„', '&dagger;': '†', '&#8224;': '†', '&Dagger;': '‡', '&#8225;': '‡', '&bull;': '•', '&#8226;': '•', '&hellip;': '…', '&#8230;': '…', '&permil;': '‰', '&#8240;': '‰', '&prime;': '′', '&#8242;': '′', '&Prime;': '″', '&#8243;': '″', '&lsaquo;': '‹', '&#8249;': '‹', '&rsaquo;': '›', '&#8250;': '›', '&oline;': '‾', '&#8254;': '‾', '&euro;': '€', '&#8364;': '€', '&trade;': '™', '&#8482;': '™', '&larr;': '←', '&#8592;': '←', '&uarr;': '↑', '&#8593;': '↑', '&rarr;': '→', '&#8594;': '→', '&darr;': '↓', '&#8595;': '↓', '&harr;': '↔', '&#8596;': '↔', '&crarr;': '↵', '&#8629;': '↵', '&lceil;': '⌈', '&#8968;': '⌈', '&rceil;': '⌉', '&#8969;': '⌉', '&lfloor;': '⌊', '&#8970;': '⌊', '&rfloor;': '⌋', '&#8971;': '⌋', '&loz;': '◊', '&#9674;': '◊', '&spades;': '♠', '&#9824;': '♠', '&clubs;': '♣', '&#9827;': '♣', '&hearts;': '♥', '&#9829;': '♥', '&diams;': '♦', '&#9830;': '♦'}
    HTML_ENTITIES = {'&#32;': ' ', '&#33;': '!', '&quot;': '"', '&#34;': '"', '&#35;': '#', '&#36;': '$', '&#37;': '%', '&amp;': '&', '&#38;': '&', '&#39;': "'", '&#40;': '(', '&#41;': ')', '&#42;': '*', '&#43;': '+', '&#44;': ',', '&#45;': '-', '&#46;': '.', '&#47;': '/', '&#48;': '0', '&#49;': '1', '&#50;': '2', '&#51;': '3', '&#52;': '4', '&#53;': '5', '&#54;': '6', '&#55;': '7', '&#56;': '8', '&#57;': '9', '&#58;': ':', '&#59;': ';', '&lt;': '<', '&#60;': '<', '&#61;': '=', '&gt;': '>', '&#62;': '>', '&#63;': '?', '&#64;': '@', '&#65;': 'A', '&#66;': 'B', '&#67;': 'C', '&#68;': 'D', '&#69;': 'E', '&#70;': 'F', '&#71;': 'G', '&#72;': 'H', '&#73;': 'I', '&#74;': 'J', '&#75;': 'K', '&#76;': 'L', '&#77;': 'M', '&#78;': 'N', '&#79;': 'O', '&#80;': 'P', '&#81;': 'Q', '&#82;': 'R', '&#83;': 'S', '&#84;': 'T', '&#85;': 'U', '&#86;': 'V', '&#87;': 'W', '&#88;': 'X', '&#89;': 'Y', '&#90;': 'Z', '&#91;': '[', '&#92;': '\\', '&#93;': ']', '&#94;': '^', '&#95;': '_', '&#96;': '`', '&#97;': 'a', '&#98;': 'b', '&#99;': 'c', '&#100;': 'd', '&#101;': 'e', '&#102;': 'f', '&#103;': 'g', '&#104;': 'h', '&#105;': 'i', '&#106;': 'j', '&#107;': 'k', '&#108;': 'l', '&#109;': 'm', '&#110;': 'n', '&#111;': 'o', '&#112;': 'p', '&#113;': 'q', '&#114;': 'r', '&#115;': 's', '&#116;': 't', '&#117;': 'u', '&#118;': 'v', '&#119;': 'w', '&#120;': 'x', '&#121;': 'y', '&#122;': 'z', '&#123;': '{', '&#124;': '|', '&#125;': '}', '&#126;': '~', '&#160;': '', '&nbsp;': '', '&#161;': '¡', '&iexcl;': '¡', '&#162;': '¢', '&cent;': '¢', '&#163;': '£', '&pound;': '£', '&#164;': '¤', '&curren;': '¤', '&#165;': '¥', '&yen;': '¥', '&#166;': '¦', '&brvbar;': '¦', '&#167;': '§', '&sect;': '§', '&#168;': '¨', '&uml;': '¨', '&#169;': '©', '&copy;': '©', '&#170;': 'ª', '&ordf;': 'ª', '&#171;': '«', '&laquo;': '«', '&#172;': '¬', '&not;': '¬', '&#173;': '\xad', '&shy;': '\xad', '&#174;': '®', '&reg;': '®', '&#175;': '¯', '&macr;': '¯', '&#176;': '°', '&deg;': '°', '&#177;': '±', '&plusmn;': '±', '&#178;': '²', '&sup2;': '²', '&#179;': '³', '&sup3;': '³', '&#180;': '´', '&acute;': '´', '&#181;': 'µ', '&micro;': 'µ', '&#182;': '¶', '&para;': '¶', '&#184;': '¸', '&cedil;': '¸', '&#185;': '¹', '&sup1;': '¹', '&#186;': 'º', '&ordm;': 'º', '&#187;': '»', '&raquo;': '»', '&#188;': '¼', '&frac14;': '¼', '&#189;': '½', '&frac12;': '½', '&#190;': '¾', '&frac34;': '¾', '&#191;': '¿', '&iquest;': '¿', '&#215;': '×', '&times;': '×', '&#247;': '÷', '&divide;': '÷', '&#8704;': '∀', '&forall;': '∀', '&#8706;': '∂', '&part;': '∂', '&#8707;': '∃', '&exist;': '∃', '&#8709;': '∅', '&empty;': '∅', '&#8711;': '∇', '&nabla;': '∇', '&#8712;': '∈', '&isin;': '∈', '&#8713;': '∉', '&notin;': '∉', '&#8715;': '∋', '&ni;': '∋', '&#8719;': '∏', '&prod;': '∏', '&#8721;': '∑', '&sum;': '∑', '&#8722;': '−', '&minus;': '−', '&#8727;': '∗', '&lowast;': '∗', '&#8730;': '√', '&radic;': '√', '&#8733;': '∝', '&prop;': '∝', '&#8734;': '∞', '&infin;': '∞', '&#8736;': '∠', '&ang;': '∠', '&#8743;': '∧', '&and;': '∧', '&#8744;': '∨', '&or;': '∨', '&#8745;': '∩', '&cap;': '∩', '&#8746;': '∪', '&cup;': '∪', '&#8747;': '∫', '&int;': '∫', '&#8756;': '∴', '&there4;': '∴', '&#8764;': '∼', '&sim;': '∼', '&#8773;': '≅', '&cong;': '≅', '&#8776;': '≈', '&asymp;': '≈', '&#8800;': '≠', '&ne;': '≠', '&#8801;': '≡', '&equiv;': '≡', '&#8804;': '≤', '&le;': '≤', '&#8805;': '≥', '&ge;': '≥', '&#8834;': '⊂', '&sub;': '⊂', '&#8835;': '⊃', '&sup;': '⊃', '&#8836;': '⊄', '&nsub;': '⊄', '&#8838;': '⊆', '&sube;': '⊆', '&#8839;': '⊇', '&supe;': '⊇', '&#8853;': '⊕', '&oplus;': '⊕', '&#8855;': '⊗', '&otimes;': '⊗', '&#8869;': '⊥', '&perp;': '⊥', '&#8901;': '⋅', '&sdot;': '⋅', '&#913;': 'Α', '&Alpha;': 'Α', '&#914;': 'Β', '&Beta;': 'Β', '&#915;': 'Γ', '&Gamma;': 'Γ', '&#916;': 'Δ', '&Delta;': 'Δ', '&#917;': 'Ε', '&Epsilon;': 'Ε', '&#918;': 'Ζ', '&Zeta;': 'Ζ', '&#919;': 'Η', '&Eta;': 'Η', '&#920;': 'Θ', '&Theta;': 'Θ', '&#921;': 'Ι', '&Iota;': 'Ι', '&#922;': 'Κ', '&Kappa;': 'Κ', '&#923;': 'Λ', '&Lambda;': 'Λ', '&#924;': 'Μ', '&Mu;': 'Μ', '&#925;': 'Ν', '&Nu;': 'Ν', '&#926;': 'Ξ', '&Xi;': 'Ξ', '&#927;': 'Ο', '&Omicron;': 'Ο', '&#928;': 'Π', '&Pi;': 'Π', '&#929;': 'Ρ', '&Rho;': 'Ρ', '&#931;': 'Σ', '&Sigma;': 'Σ', '&#932;': 'Τ', '&Tau;': 'Τ', '&#933;': 'Υ', '&Upsilon;': 'Υ', '&#934;': 'Φ', '&Phi;': 'Φ', '&#935;': 'Χ', '&Chi;': 'Χ', '&#936;': 'Ψ', '&Psi;': 'Ψ', '&#937;': 'Ω', '&Omega;': 'Ω', '&#945;': 'α', '&alpha;': 'α', '&#946;': 'β', '&beta;': 'β', '&#947;': 'γ', '&gamma;': 'γ', '&#948;': 'δ', '&delta;': 'δ', '&#949;': 'ε', '&epsilon;': 'ε', '&#950;': 'ζ', '&zeta;': 'ζ', '&#951;': 'η', '&eta;': 'η', '&#952;': 'θ', '&theta;': 'θ', '&#953;': 'ι', '&iota;': 'ι', '&#954;': 'κ', '&kappa;': 'κ', '&#955;': 'λ', '&lambda;': 'λ', '&#956;': 'μ', '&mu;': 'μ', '&#957;': 'ν', '&nu;': 'ν', '&#958;': 'ξ', '&xi;': 'ξ', '&#959;': 'ο', '&omicron;': 'ο', '&#960;': 'π', '&pi;': 'π', '&#961;': 'ρ', '&rho;': 'ρ', '&#962;': 'ς', '&sigmaf;': 'ς', '&#963;': 'σ', '&sigma;': 'σ', '&#964;': 'τ', '&tau;': 'τ', '&#965;': 'υ', '&upsilon;': 'υ', '&#966;': 'φ', '&phi;': 'φ', '&#967;': 'χ', '&chi;': 'χ', '&#968;': 'ψ', '&psi;': 'ψ', '&#969;': 'ω', '&omega;': 'ω', '&#977;': 'ϑ', '&thetasym;': 'ϑ', '&#978;': 'ϒ', '&upsih;': 'ϒ', '&#982;': 'ϖ', '&piv;': 'ϖ', '&OElig;': 'Œ', '&#338;': 'Œ', '&oelig;': 'œ', '&#339;': 'œ', '&Scaron;': 'Š', '&#352;': 'Š', '&scaron;': 'š', '&#353;': 'š', '&Yuml;': 'Ÿ', '&#376;': 'Ÿ', '&fnof;': 'ƒ', '&#402;': 'ƒ', '&circ;': 'ˆ', '&#710;': 'ˆ', '&tilde;': '˜', '&#732;': '˜', '&ensp;': '\u2002', '&#8194;': '\u2002', '&emsp;': '\u2003', '&#8195;': '\u2003', '&thinsp;': '\u2009', '&#8201;': '\u2009', '&zwnj;': '\u200c', '&#8204;': '\u200c', '&zwj;': '\u200d', '&#8205;': '\u200d', '&lrm;': '\u200e', '&#8206;': '\u200e', '&rlm;': '\u200f', '&#8207;': '\u200f', '&ndash;': '–', '&#8211;': '–', '&mdash;': '—', '&#8212;': '—', '&lsquo;': '‘', '&#8216;': '‘', '&rsquo;': '’', '&#8217;': '’', '&sbquo;': '‚', '&#8218;': '‚', '&ldquo;': '“', '&#8220;': '“', '&rdquo;': '”', '&#8221;': '”', '&bdquo;': '„', '&#8222;': '„', '&dagger;': '†', '&#8224;': '†', '&Dagger;': '‡', '&#8225;': '‡', '&bull;': '•', '&#8226;': '•', '&hellip;': '…', '&#8230;': '…', '&permil;': '‰', '&#8240;': '‰', '&prime;': '′', '&#8242;': '′', '&Prime;': '″', '&#8243;': '″', '&lsaquo;': '‹', '&#8249;': '‹', '&rsaquo;': '›', '&#8250;': '›', '&oline;': '‾', '&#8254;': '‾', '&euro;': '€', '&#8364;': '€', '&trade;': '™', '&#8482;': '™', '&larr;': '←', '&#8592;': '←', '&uarr;': '↑', '&#8593;': '↑', '&rarr;': '→', '&#8594;': '→', '&darr;': '↓', '&#8595;': '↓', '&harr;': '↔', '&#8596;': '↔', '&crarr;': '↵', '&#8629;': '↵', '&lceil;': '⌈', '&#8968;': '⌈', '&rceil;': '⌉', '&#8969;': '⌉', '&lfloor;': '⌊', '&#8970;': '⌊', '&rfloor;': '⌋', '&#8971;': '⌋', '&loz;': '◊', '&#9674;': '◊', '&spades;': '♠', '&#9824;': '♠', '&clubs;': '♣', '&#9827;': '♣', '&hearts;': '♥', '&#9829;': '♥', '&diams;': '♦', '&#9830;': '♦'}