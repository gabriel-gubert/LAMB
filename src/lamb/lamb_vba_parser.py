from antlr4 import ParseTreeWalker
from lamb_antlr4_vba import VbaParser
from lamb_antlr4_vba import vbaListener


class LambVbaListener(vbaListener.vbaListener):
    def __init__(self):
        self._identifiers: set = set()


    def enterAmbiguousIdentifier(self, ctx):
        self._identifiers.add(ctx.getText())


    def enterCertainIdentifier(self, ctx):
        self._identifiers.add(ctx.getText())


class LambVbaParser:
    def __init__(self, vba_code: str):
        if not isinstance(vba_code, str):
            raise TypeError("vba_code must be a string.")

        parser_wrapper = VbaParser()

        tree, _ = parser_wrapper.parse(vba_code)

        self._listener = LambVbaListener()
        walker = ParseTreeWalker()

        walker.walk(self._listener, tree)


    def get_identifiers(self) -> set:
        return self._listener._identifiers