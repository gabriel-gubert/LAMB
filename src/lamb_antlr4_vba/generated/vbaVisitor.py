# Generated from src/catialyst-antlr4-vba/grammar/vba.g4 by ANTLR 4.13.1
from antlr4 import *
if "." in __name__:
    from .vbaParser import vbaParser
else:
    from vbaParser import vbaParser

# This class defines a complete generic visitor for a parse tree produced by vbaParser.

class vbaVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by vbaParser#startRule.
    def visitStartRule(self, ctx:vbaParser.StartRuleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#module.
    def visitModule(self, ctx:vbaParser.ModuleContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#moduleHeader.
    def visitModuleHeader(self, ctx:vbaParser.ModuleHeaderContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#moduleConfig.
    def visitModuleConfig(self, ctx:vbaParser.ModuleConfigContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#moduleConfigElement.
    def visitModuleConfigElement(self, ctx:vbaParser.ModuleConfigElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#moduleAttributes.
    def visitModuleAttributes(self, ctx:vbaParser.ModuleAttributesContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#moduleDeclarations.
    def visitModuleDeclarations(self, ctx:vbaParser.ModuleDeclarationsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#optionBaseStmt.
    def visitOptionBaseStmt(self, ctx:vbaParser.OptionBaseStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#optionCompareStmt.
    def visitOptionCompareStmt(self, ctx:vbaParser.OptionCompareStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#optionExplicitStmt.
    def visitOptionExplicitStmt(self, ctx:vbaParser.OptionExplicitStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#optionPrivateModuleStmt.
    def visitOptionPrivateModuleStmt(self, ctx:vbaParser.OptionPrivateModuleStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#moduleDeclarationsElement.
    def visitModuleDeclarationsElement(self, ctx:vbaParser.ModuleDeclarationsElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#macroStmt.
    def visitMacroStmt(self, ctx:vbaParser.MacroStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#moduleBody.
    def visitModuleBody(self, ctx:vbaParser.ModuleBodyContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#moduleBodyElement.
    def visitModuleBodyElement(self, ctx:vbaParser.ModuleBodyElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#attributeStmt.
    def visitAttributeStmt(self, ctx:vbaParser.AttributeStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#block.
    def visitBlock(self, ctx:vbaParser.BlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#blockStmt.
    def visitBlockStmt(self, ctx:vbaParser.BlockStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#appactivateStmt.
    def visitAppactivateStmt(self, ctx:vbaParser.AppactivateStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#beepStmt.
    def visitBeepStmt(self, ctx:vbaParser.BeepStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#chdirStmt.
    def visitChdirStmt(self, ctx:vbaParser.ChdirStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#chdriveStmt.
    def visitChdriveStmt(self, ctx:vbaParser.ChdriveStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#closeStmt.
    def visitCloseStmt(self, ctx:vbaParser.CloseStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#constStmt.
    def visitConstStmt(self, ctx:vbaParser.ConstStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#constSubStmt.
    def visitConstSubStmt(self, ctx:vbaParser.ConstSubStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#dateStmt.
    def visitDateStmt(self, ctx:vbaParser.DateStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#declareStmt.
    def visitDeclareStmt(self, ctx:vbaParser.DeclareStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#deftypeStmt.
    def visitDeftypeStmt(self, ctx:vbaParser.DeftypeStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#deleteSettingStmt.
    def visitDeleteSettingStmt(self, ctx:vbaParser.DeleteSettingStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#doLoopStmt.
    def visitDoLoopStmt(self, ctx:vbaParser.DoLoopStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#endStmt.
    def visitEndStmt(self, ctx:vbaParser.EndStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#enumerationStmt.
    def visitEnumerationStmt(self, ctx:vbaParser.EnumerationStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#enumerationStmt_Constant.
    def visitEnumerationStmt_Constant(self, ctx:vbaParser.EnumerationStmt_ConstantContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#eraseStmt.
    def visitEraseStmt(self, ctx:vbaParser.EraseStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#errorStmt.
    def visitErrorStmt(self, ctx:vbaParser.ErrorStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#eventStmt.
    def visitEventStmt(self, ctx:vbaParser.EventStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#exitStmt.
    def visitExitStmt(self, ctx:vbaParser.ExitStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#filecopyStmt.
    def visitFilecopyStmt(self, ctx:vbaParser.FilecopyStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#forEachStmt.
    def visitForEachStmt(self, ctx:vbaParser.ForEachStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#forNextStmt.
    def visitForNextStmt(self, ctx:vbaParser.ForNextStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#functionStmt.
    def visitFunctionStmt(self, ctx:vbaParser.FunctionStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#getStmt.
    def visitGetStmt(self, ctx:vbaParser.GetStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#goSubStmt.
    def visitGoSubStmt(self, ctx:vbaParser.GoSubStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#goToStmt.
    def visitGoToStmt(self, ctx:vbaParser.GoToStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#inlineIfThenElse.
    def visitInlineIfThenElse(self, ctx:vbaParser.InlineIfThenElseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#blockIfThenElse.
    def visitBlockIfThenElse(self, ctx:vbaParser.BlockIfThenElseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#ifBlockStmt.
    def visitIfBlockStmt(self, ctx:vbaParser.IfBlockStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#ifConditionStmt.
    def visitIfConditionStmt(self, ctx:vbaParser.IfConditionStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#ifElseIfBlockStmt.
    def visitIfElseIfBlockStmt(self, ctx:vbaParser.IfElseIfBlockStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#ifElseBlockStmt.
    def visitIfElseBlockStmt(self, ctx:vbaParser.IfElseBlockStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#implementsStmt.
    def visitImplementsStmt(self, ctx:vbaParser.ImplementsStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#inputStmt.
    def visitInputStmt(self, ctx:vbaParser.InputStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#killStmt.
    def visitKillStmt(self, ctx:vbaParser.KillStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#letStmt.
    def visitLetStmt(self, ctx:vbaParser.LetStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#lineInputStmt.
    def visitLineInputStmt(self, ctx:vbaParser.LineInputStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#lineNumber.
    def visitLineNumber(self, ctx:vbaParser.LineNumberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#loadStmt.
    def visitLoadStmt(self, ctx:vbaParser.LoadStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#lockStmt.
    def visitLockStmt(self, ctx:vbaParser.LockStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#lsetStmt.
    def visitLsetStmt(self, ctx:vbaParser.LsetStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#macroConstStmt.
    def visitMacroConstStmt(self, ctx:vbaParser.MacroConstStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#macroIfThenElseStmt.
    def visitMacroIfThenElseStmt(self, ctx:vbaParser.MacroIfThenElseStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#macroIfBlockStmt.
    def visitMacroIfBlockStmt(self, ctx:vbaParser.MacroIfBlockStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#macroElseIfBlockStmt.
    def visitMacroElseIfBlockStmt(self, ctx:vbaParser.MacroElseIfBlockStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#macroElseBlockStmt.
    def visitMacroElseBlockStmt(self, ctx:vbaParser.MacroElseBlockStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#midStmt.
    def visitMidStmt(self, ctx:vbaParser.MidStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#mkdirStmt.
    def visitMkdirStmt(self, ctx:vbaParser.MkdirStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#nameStmt.
    def visitNameStmt(self, ctx:vbaParser.NameStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#onErrorStmt.
    def visitOnErrorStmt(self, ctx:vbaParser.OnErrorStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#onGoToStmt.
    def visitOnGoToStmt(self, ctx:vbaParser.OnGoToStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#onGoSubStmt.
    def visitOnGoSubStmt(self, ctx:vbaParser.OnGoSubStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#openStmt.
    def visitOpenStmt(self, ctx:vbaParser.OpenStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#outputList.
    def visitOutputList(self, ctx:vbaParser.OutputListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#outputList_Expression.
    def visitOutputList_Expression(self, ctx:vbaParser.OutputList_ExpressionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#printStmt.
    def visitPrintStmt(self, ctx:vbaParser.PrintStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#propertyGetStmt.
    def visitPropertyGetStmt(self, ctx:vbaParser.PropertyGetStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#propertySetStmt.
    def visitPropertySetStmt(self, ctx:vbaParser.PropertySetStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#propertyLetStmt.
    def visitPropertyLetStmt(self, ctx:vbaParser.PropertyLetStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#putStmt.
    def visitPutStmt(self, ctx:vbaParser.PutStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#raiseEventStmt.
    def visitRaiseEventStmt(self, ctx:vbaParser.RaiseEventStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#randomizeStmt.
    def visitRandomizeStmt(self, ctx:vbaParser.RandomizeStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#redimStmt.
    def visitRedimStmt(self, ctx:vbaParser.RedimStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#redimSubStmt.
    def visitRedimSubStmt(self, ctx:vbaParser.RedimSubStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#resetStmt.
    def visitResetStmt(self, ctx:vbaParser.ResetStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#resumeStmt.
    def visitResumeStmt(self, ctx:vbaParser.ResumeStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#returnStmt.
    def visitReturnStmt(self, ctx:vbaParser.ReturnStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#rmdirStmt.
    def visitRmdirStmt(self, ctx:vbaParser.RmdirStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#rsetStmt.
    def visitRsetStmt(self, ctx:vbaParser.RsetStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#savepictureStmt.
    def visitSavepictureStmt(self, ctx:vbaParser.SavepictureStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#saveSettingStmt.
    def visitSaveSettingStmt(self, ctx:vbaParser.SaveSettingStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#seekStmt.
    def visitSeekStmt(self, ctx:vbaParser.SeekStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#selectCaseStmt.
    def visitSelectCaseStmt(self, ctx:vbaParser.SelectCaseStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#caseCondIs.
    def visitCaseCondIs(self, ctx:vbaParser.CaseCondIsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#caseCondTo.
    def visitCaseCondTo(self, ctx:vbaParser.CaseCondToContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#caseCondValue.
    def visitCaseCondValue(self, ctx:vbaParser.CaseCondValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#sC_Case.
    def visitSC_Case(self, ctx:vbaParser.SC_CaseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#caseCondElse.
    def visitCaseCondElse(self, ctx:vbaParser.CaseCondElseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#caseCondSelection.
    def visitCaseCondSelection(self, ctx:vbaParser.CaseCondSelectionContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#sendkeysStmt.
    def visitSendkeysStmt(self, ctx:vbaParser.SendkeysStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#setattrStmt.
    def visitSetattrStmt(self, ctx:vbaParser.SetattrStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#setStmt.
    def visitSetStmt(self, ctx:vbaParser.SetStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#stopStmt.
    def visitStopStmt(self, ctx:vbaParser.StopStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#subStmt.
    def visitSubStmt(self, ctx:vbaParser.SubStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#timeStmt.
    def visitTimeStmt(self, ctx:vbaParser.TimeStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#typeStmt.
    def visitTypeStmt(self, ctx:vbaParser.TypeStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#typeStmt_Element.
    def visitTypeStmt_Element(self, ctx:vbaParser.TypeStmt_ElementContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#typeOfStmt.
    def visitTypeOfStmt(self, ctx:vbaParser.TypeOfStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#unloadStmt.
    def visitUnloadStmt(self, ctx:vbaParser.UnloadStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#unlockStmt.
    def visitUnlockStmt(self, ctx:vbaParser.UnlockStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsAssign.
    def visitVsAssign(self, ctx:vbaParser.VsAssignContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsPlus.
    def visitVsPlus(self, ctx:vbaParser.VsPlusContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsNot.
    def visitVsNot(self, ctx:vbaParser.VsNotContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsStruct.
    def visitVsStruct(self, ctx:vbaParser.VsStructContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsTypeOf.
    def visitVsTypeOf(self, ctx:vbaParser.VsTypeOfContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsICS.
    def visitVsICS(self, ctx:vbaParser.VsICSContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsRelational.
    def visitVsRelational(self, ctx:vbaParser.VsRelationalContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsAddMinus.
    def visitVsAddMinus(self, ctx:vbaParser.VsAddMinusContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsXor.
    def visitVsXor(self, ctx:vbaParser.VsXorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsDivMult.
    def visitVsDivMult(self, ctx:vbaParser.VsDivMultContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsAnd.
    def visitVsAnd(self, ctx:vbaParser.VsAndContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsPow.
    def visitVsPow(self, ctx:vbaParser.VsPowContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsMod.
    def visitVsMod(self, ctx:vbaParser.VsModContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsAmp.
    def visitVsAmp(self, ctx:vbaParser.VsAmpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsAddressOf.
    def visitVsAddressOf(self, ctx:vbaParser.VsAddressOfContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsNew.
    def visitVsNew(self, ctx:vbaParser.VsNewContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsOr.
    def visitVsOr(self, ctx:vbaParser.VsOrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsLiteral.
    def visitVsLiteral(self, ctx:vbaParser.VsLiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsEqv.
    def visitVsEqv(self, ctx:vbaParser.VsEqvContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsNegation.
    def visitVsNegation(self, ctx:vbaParser.VsNegationContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsImp.
    def visitVsImp(self, ctx:vbaParser.VsImpContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#vsMid.
    def visitVsMid(self, ctx:vbaParser.VsMidContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#variableStmt.
    def visitVariableStmt(self, ctx:vbaParser.VariableStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#variableListStmt.
    def visitVariableListStmt(self, ctx:vbaParser.VariableListStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#variableSubStmt.
    def visitVariableSubStmt(self, ctx:vbaParser.VariableSubStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#whileWendStmt.
    def visitWhileWendStmt(self, ctx:vbaParser.WhileWendStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#widthStmt.
    def visitWidthStmt(self, ctx:vbaParser.WidthStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#withStmt.
    def visitWithStmt(self, ctx:vbaParser.WithStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#writeStmt.
    def visitWriteStmt(self, ctx:vbaParser.WriteStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#fileNumber.
    def visitFileNumber(self, ctx:vbaParser.FileNumberContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#explicitCallStmt.
    def visitExplicitCallStmt(self, ctx:vbaParser.ExplicitCallStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#eCS_ProcedureCall.
    def visitECS_ProcedureCall(self, ctx:vbaParser.ECS_ProcedureCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#eCS_MemberProcedureCall.
    def visitECS_MemberProcedureCall(self, ctx:vbaParser.ECS_MemberProcedureCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#implicitCallStmt_InBlock.
    def visitImplicitCallStmt_InBlock(self, ctx:vbaParser.ImplicitCallStmt_InBlockContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#iCS_B_MemberProcedureCall.
    def visitICS_B_MemberProcedureCall(self, ctx:vbaParser.ICS_B_MemberProcedureCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#iCS_B_ProcedureCall.
    def visitICS_B_ProcedureCall(self, ctx:vbaParser.ICS_B_ProcedureCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#implicitCallStmt_InStmt.
    def visitImplicitCallStmt_InStmt(self, ctx:vbaParser.ImplicitCallStmt_InStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#iCS_S_VariableOrProcedureCall.
    def visitICS_S_VariableOrProcedureCall(self, ctx:vbaParser.ICS_S_VariableOrProcedureCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#iCS_S_ProcedureOrArrayCall.
    def visitICS_S_ProcedureOrArrayCall(self, ctx:vbaParser.ICS_S_ProcedureOrArrayCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#iCS_S_MembersCall.
    def visitICS_S_MembersCall(self, ctx:vbaParser.ICS_S_MembersCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#iCS_S_MemberCall.
    def visitICS_S_MemberCall(self, ctx:vbaParser.ICS_S_MemberCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#iCS_S_DictionaryCall.
    def visitICS_S_DictionaryCall(self, ctx:vbaParser.ICS_S_DictionaryCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#argsCall.
    def visitArgsCall(self, ctx:vbaParser.ArgsCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#argCall.
    def visitArgCall(self, ctx:vbaParser.ArgCallContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#dictionaryCallStmt.
    def visitDictionaryCallStmt(self, ctx:vbaParser.DictionaryCallStmtContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#argList.
    def visitArgList(self, ctx:vbaParser.ArgListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#arg.
    def visitArg(self, ctx:vbaParser.ArgContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#argDefaultValue.
    def visitArgDefaultValue(self, ctx:vbaParser.ArgDefaultValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#subscripts.
    def visitSubscripts(self, ctx:vbaParser.SubscriptsContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#subscript_.
    def visitSubscript_(self, ctx:vbaParser.Subscript_Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#ambiguousIdentifier.
    def visitAmbiguousIdentifier(self, ctx:vbaParser.AmbiguousIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#asTypeClause.
    def visitAsTypeClause(self, ctx:vbaParser.AsTypeClauseContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#baseType.
    def visitBaseType(self, ctx:vbaParser.BaseTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#certainIdentifier.
    def visitCertainIdentifier(self, ctx:vbaParser.CertainIdentifierContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#comparisonOperator.
    def visitComparisonOperator(self, ctx:vbaParser.ComparisonOperatorContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#complexType.
    def visitComplexType(self, ctx:vbaParser.ComplexTypeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#fieldLength.
    def visitFieldLength(self, ctx:vbaParser.FieldLengthContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#letterrange.
    def visitLetterrange(self, ctx:vbaParser.LetterrangeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#lineLabel.
    def visitLineLabel(self, ctx:vbaParser.LineLabelContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#literal.
    def visitLiteral(self, ctx:vbaParser.LiteralContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#type_.
    def visitType_(self, ctx:vbaParser.Type_Context):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#typeHint.
    def visitTypeHint(self, ctx:vbaParser.TypeHintContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#visibility.
    def visitVisibility(self, ctx:vbaParser.VisibilityContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#ambiguousKeyword.
    def visitAmbiguousKeyword(self, ctx:vbaParser.AmbiguousKeywordContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#remComment.
    def visitRemComment(self, ctx:vbaParser.RemCommentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#comment.
    def visitComment(self, ctx:vbaParser.CommentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#endOfLine.
    def visitEndOfLine(self, ctx:vbaParser.EndOfLineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by vbaParser#endOfStatement.
    def visitEndOfStatement(self, ctx:vbaParser.EndOfStatementContext):
        return self.visitChildren(ctx)



del vbaParser