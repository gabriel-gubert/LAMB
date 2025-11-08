import os
from tree_sitter import Language, Parser
import tree_sitter_html as tshtml
from .trees import HTMLTree

SUPPORTED_LANGUAGES = ['html']

def get_file_extension(language: str):
	LANGUAGE_TO_FILE_EXTENSION_MAP = {
		'html': ['htm', 'html']
	}

	return LANGUAGE_TO_FILE_EXTENSION_MAP[language.lower()]

def parse(filepath: str, encoding: str = 'utf-8'):
    ''' Parse a Source-Code File. Returns a Wrapper for a Tree-sitter Tree. '''

    file = open(filepath, 'r', encoding = encoding)

    basename = os.path.basename(filepath)
    filename = str.join('.', basename.split('.')[:-1])
    suffix = basename.split('.')[-1]

    if suffix in get_file_extension('html'):
        HTML_LANGUAGE = Language(tshtml.language())
        parser = Parser(HTML_LANGUAGE)
        language = 'html'
        tree = HTMLTree
    else:
        file_extensions = []
        for language in SUPPORTED_LANGUAGES:
            for file_extension in get_file_extension(language):
                if file_extension in file_extensions:
                    continue

                file_extensions.append(file_extension)

        raise ValueError(f'Unrecognized File Extension. Expect {file_extensions}, is "{suffix}".')

    tstree = parser.parse(bytes(file.read(), encoding = encoding))

    return tree(tstree, filepath, language, encoding)

def parse_content(content: str, language: str, encoding: str = 'utf-8'):
    ''' Parse a Source-Code File's Content. Returns a Wrapper for a Tree-sitter Tree. '''

    if language.lower() == 'html':
        HTML_LANGUAGE = Language(tshtml.language())
        parser = Parser(HTML_LANGUAGE)
        tree = HTMLTree
    else:
        raise ValueError(f'Unsupported Language. Expect {SUPPORTED_LANGUAGES}, is "{language}".')

    tstree = parser.parse(bytes(content, encoding = encoding))

    return tree(tstree, '', language = language, encoding = encoding)