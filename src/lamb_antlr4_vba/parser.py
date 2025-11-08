from antlr4 import InputStream, CommonTokenStream
from .generated.vbaLexer import vbaLexer
from .generated.vbaParser import vbaParser

class VbaParser:
    def parse(self, code: str, start_rule_name: str = 'startRule'):
        input_stream = InputStream(code)
        lexer = vbaLexer(input_stream)
        stream = CommonTokenStream(lexer)
        parser = vbaParser(stream)
        start_rule = getattr(parser, start_rule_name)
        tree = start_rule()

        return tree, parser
