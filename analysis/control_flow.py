#!/usr/bin/env python3

import networkx as nx

from lian.config import config,schema
from lian.util import util
from lian.util import dataframe_operation as do
from lian.config.constants import (
    ControlFlowKind,
    AnalysisPhaseName
)
from lian.semantic.internal.internal_structure import (
    ControlFlowGraph,
    CFGNode,
    InternalAnalysisTemplate
)

class ControlFlowAnalysis(InternalAnalysisTemplate):
    def init(self):
        self.name = AnalysisPhaseName.ControlFlowGraph
        self.description = "control flow graph analysis"

        self.stmt_handlers = {
            "if_stmt"       : self.analyze_if_stmt,
            "while_stmt"    : self.analyze_while_stmt,
            "dowhile_stmt"  : self.analyze_dowhile_stmt,
            "for_stmt"      : self.analyze_for_stmt,
            "forin_stmt"    : self.analyze_while_stmt,
            "break_stmt"    : self.analyze_break_stmt,
            "continue_stmt" : self.analyze_continue_stmt,
            "try_stmt"      : self.analyze_try_stmt,
            "return_stmt"   : self.analyze_return_stmt,
            "yield"         : self.analyze_yield_stmt,
            "method_decl"   : self.analyze_method_decl_stmt,
            "class_decl"    : self.analyze_decl_stmt,
            "record_decl"   : self.analyze_decl_stmt,
            "interface_decl": self.analyze_decl_stmt,
            "struct_decl"   : self.analyze_decl_stmt,
        }


    def unit_analysis_start(self):
        pass

    def unit_analysis_end(self):
        pass

    def bundle_start(self):
        self.all_cfg_edges = []
        self.cfg = None

    def bundle_end(self):
        semantic_path = self.bundle_path.replace(f"/{config.GLANG_DIR}/", f"/{config.SEMANTIC_DIR}/")
        cfg_final_path = semantic_path + config.CONTROL_FLOW_GRAPH_EXT
        data_model = do.DataFrameAgent(self.all_cfg_edges, columns = schema.control_flow_graph_schema)
        data_model.save(cfg_final_path)
        self.module_symbols.update_cfg_path_by_glang_path(self.bundle_path, cfg_final_path)
        if self.options.debug and self.cfg is not None:
            cfg_png_path = semantic_path + "_cfg.png"
            self.cfg.save_png(cfg_png_path)

    def replace_multiple_edges_with_single(self):
        flag = True
        old_graph = self.cfg.graph
        for u, v in old_graph.edges():
            if old_graph.number_of_edges(u, v) > 1:
                flag = False
                break

        if flag:
            return

        new_graph = nx.DiGraph()
        for u, v in old_graph.edges():
            if old_graph.number_of_edges(u, v) > 1:
                # total_weight = sum(old_graph[u][v][key]['weight'] for key in old_graph[u][v])
                new_graph.add_edge(u, v, weight = ControlFlowKind.EMPTY)
            else:
                if not new_graph.has_edge(u, v):
                    new_graph.add_edge(u, v, weight = old_graph[u][v][0]['weight'])
        self.cfg.graph = new_graph

    def save_current_cfg(self):
        edges = []
        edges_with_weights = self.cfg.graph.edges(data='weight', default = 0)
        for e in edges_with_weights:
            edges.append((
                self.cfg.unit_id,
                self.cfg.method_id,
                e[0],
                e[1],
                0 if util.is_empty(e[2]) else e[2]
            ))
        self.all_cfg_edges.extend(edges)
            
    def read_block(self, parent, block_id):
        return parent.read_block(block_id, reset_index = True)
        # return self.method_body.read_block(block_id, reset_index = True)

    def boundary_of_multi_blocks(self, block, block_ids):
        return block.boundary_of_multi_blocks(block_ids)

    def method_analysis(self, previous_results):
        self.cfg = ControlFlowGraph(self.unit_info, self.method_stmt)

        last_stmts_init = self.analyze_init_block(self.method_init)
        last_stmts = self.analyze_block(self.method_body, last_stmts_init)
        if last_stmts:
            self.cfg.add_edge(last_stmts, -1)
        self.replace_multiple_edges_with_single()
        self.save_current_cfg()
        return self.cfg.graph

    def analyze_while_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # 将父语句链接到当前的 while 语句
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)

        # 为 while 语句的条件创建 CFGNode
        condition_node = CFGNode(current_stmt, ControlFlowKind.LOOP_TRUE)

        # 分析 while 语句的主体
        while_body_id = current_stmt.body
        if not util.isna(while_body_id):
            while_body = self.read_block(current_block, while_body_id)
            if len(while_body) != 0:
                # 递归分析 while 循环的主体
                last_stmts_of_while_body = self.analyze_block(while_body, [condition_node], global_special_stmts)
                
                # 将 while 主体的最后一个语句链接回条件以形成循环
                self.link_parent_stmts_to_current_stmt(last_stmts_of_while_body, current_stmt)
        
        # 为条件为假的情况创建 CFGNode（退出循环）
        false_condition_node = CFGNode(current_stmt, ControlFlowKind.LOOP_FALSE)

        # 确定 while 循环的边界
        boundary = self.boundary_of_multi_blocks(current_block, [while_body_id])

        return ([false_condition_node], boundary)

    def analyze_dowhile_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        # 为 do-while 循环的入口创建一个 CFGNode
        do_entry_node = CFGNode(current_stmt, ControlFlowKind.LOOP_TRUE)
        
        # 分析 do-while 语句的主体
        dowhile_body_id = current_stmt.body
        if not util.isna(dowhile_body_id):
            dowhile_body = self.read_block(current_block, dowhile_body_id)
            if len(dowhile_body) != 0:
                # 递归分析 do-while 循环的主体
                last_stmts_of_dowhile_body = self.analyze_block(dowhile_body, [do_entry_node], global_special_stmts)
                
                # 将 do-while 主体的最后语句链接到条件节点
                self.link_parent_stmts_to_current_stmt(last_stmts_of_dowhile_body, current_stmt)
                
                # 将条件节点链接回入口节点以形成循环
                self.cfg.add_edge(do_entry_node.stmt, do_entry_node.stmt, ControlFlowKind.LOOP_FALSE)
        
        # 为 false 条件（从循环中退出）创建一个 CFGNode
        false_condition_node = CFGNode(current_stmt, ControlFlowKind.LOOP_FALSE)

        # 确定 do-while 循环的边界
        boundary = self.boundary_of_multi_blocks(current_block, [dowhile_body_id])

        return ([false_condition_node], boundary)

    def analyze_for_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        # 创建一个 CFGNode 作为 for 循环的入口节点
        for_entry_node = CFGNode(current_stmt, ControlFlowKind.FOR_CONDITION)
        
        # 分析 for 语句的初始化部分
        for_init_body_id = current_stmt.init_body
        if not util.isna(for_init_body_id):
            for_init_body = self.read_block(current_block, for_init_body_id)
            if len(for_init_body) != 0:
                init_last_stmts = self.analyze_block(for_init_body, [for_entry_node], global_special_stmts)
            else:
                init_last_stmts = [for_entry_node]
        else:
            init_last_stmts = [for_entry_node]
        
        # 分析 for 语句的条件前体部分
        for_condition_prebody_id = current_stmt.condition_prebody
        if not util.isna(for_condition_prebody_id):
            for_condition_prebody = self.read_block(current_block, for_condition_prebody_id)
            if len(for_condition_prebody) != 0:
                condition_prebody_last_stmts = self.analyze_block(for_condition_prebody, init_last_stmts, global_special_stmts)
            else:
                condition_prebody_last_stmts = init_last_stmts
        else:
            condition_prebody_last_stmts = init_last_stmts
        
        # 创建一个 CFGNode 作为 for 语句的真条件节点
        condition_true_node = CFGNode(current_stmt, ControlFlowKind.LOOP_TRUE)
        
        # 将条件前体的最后语句链接到真条件节点
        self.link_parent_stmts_to_current_stmt(condition_prebody_last_stmts, condition_true_node.stmt)
        
        # 分析 for 语句的主体部分
        for_body_id = current_stmt.body
        if not util.isna(for_body_id):
            for_body = self.read_block(current_block, for_body_id)
            if len(for_body) != 0:
                body_last_stmts = self.analyze_block(for_body, [condition_true_node], global_special_stmts)
            else:
                body_last_stmts = [condition_true_node]
        else:
            body_last_stmts = [condition_true_node]
        
        # 分析 for 语句的更新部分
        for_update_body_id = current_stmt.update_body
        if not util.isna(for_update_body_id):
            for_update_body = self.read_block(current_block, for_update_body_id)
            if len(for_update_body) != 0:
                update_last_stmts = self.analyze_block(for_update_body, body_last_stmts, global_special_stmts)
            else:
                update_last_stmts = body_last_stmts
        else:
            update_last_stmts = body_last_stmts
        
        # 创建一个 CFGNode 作为 for 循环的假条件节点（循环退出节点）
        condition_false_node = CFGNode(current_stmt, ControlFlowKind.LOOP_FALSE)
        
        # 将更新部分的最后语句链接回条件前体
        if not util.isna(for_condition_prebody_id):
            for_condition_prebody = self.read_block(current_block, for_condition_prebody_id)
            if len(for_condition_prebody) != 0:
                condition_prebody_last_stmts = self.analyze_block(for_condition_prebody, update_last_stmts, global_special_stmts)
            else:
                condition_prebody_last_stmts = update_last_stmts
        else:
            condition_prebody_last_stmts = update_last_stmts
        
        # 将假条件节点链接到 for 循环后的代码
        self.link_parent_stmts_to_current_stmt(condition_prebody_last_stmts, condition_false_node.stmt)
        
        # 确定 for 循环的边界
        boundary = self.boundary_of_multi_blocks(current_block, [for_init_body_id, for_condition_prebody_id, for_update_body_id, for_body_id])
        
        return ([condition_false_node], boundary)

    def analyze_return_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)

        return_node = CFGNode(current_stmt, ControlFlowKind.RETURN)
        return ([return_node], -1)

    def analyze_try_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # Link parent statements to the try statement
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        
        # Create a node for the try statement
        try_node = CFGNode(current_stmt, ControlFlowKind.TRY)
        
        # Analyze the try block
        try_body_id = current_stmt.try_body
        last_stmts_of_try = []
        if not util.isna(try_body_id):
            try_body = self.read_block(current_block, try_body_id)
            if len(try_body) != 0:
                last_stmts_of_try = self.analyze_block(try_body, [try_node], global_special_stmts)
            else:
                last_stmts_of_try = [try_node]
        
        # Analyze the catch blocks
        catch_body_ids = current_stmt.catch_bodies or []
        last_stmts_of_catch = []
        for catch_body_id in catch_body_ids:
            if not util.isna(catch_body_id):
                catch_body = self.read_block(current_block, catch_body_id)
                if len(catch_body) != 0:
                    last_stmts_of_catch.extend(self.analyze_block(catch_body, last_stmts_of_try, global_special_stmts))
                else:
                    last_stmts_of_catch.extend(last_stmts_of_try)
        
        # Analyze the finally block
        finally_body_id = current_stmt.finally_body
        last_stmts_of_finally = []
        if not util.isna(finally_body_id):
            finally_body = self.read_block(current_block, finally_body_id)
            if len(finally_body) != 0:
                last_stmts_of_finally = self.analyze_block(finally_body, last_stmts_of_try + last_stmts_of_catch, global_special_stmts)
            else:
                last_stmts_of_finally = last_stmts_of_try + last_stmts_of_catch
        else:
            last_stmts_of_finally = last_stmts_of_try + last_stmts_of_catch
        
        # Determine the boundary of the try statement
        boundary = self.boundary_of_multi_blocks(current_block, [try_body_id] + catch_body_ids + [finally_body_id])
        
        return (last_stmts_of_finally, boundary)


    def analyze_method_decl_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_decl_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        return ([], -1)

    def analyze_break_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # Link the parent statements to the current break statement
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)

        # Create a node for the break statement
        break_node = CFGNode(current_stmt, ControlFlowKind.BREAK)

        # The break statement terminates the current loop or switch, so it should have no following statements
        return ([break_node], -1)


    def analyze_continue_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # Link the parent statements to the current continue statement
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)

        # Create a node for the continue statement
        continue_node = CFGNode(current_stmt, ControlFlowKind.CONTINUE)

        # The continue statement jumps to the next iteration of the loop, so it should have no following statements within the current iteration
        return ([continue_node], -1)

    def analyze_yield_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        # Link parent statements to the yield statement
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)

        # Create a node for the yield statement
        yield_node = CFGNode(current_stmt, ControlFlowKind.YIELD)

        # Add edge from yield node to the next statement (if any) or to exit
        self.cfg.add_edge(yield_node.stmt, -1, ControlFlowKind.YIELD)

        # Return the yield node as the last statement
        return ([yield_node], -1)


    def analyze_if_stmt(self, current_block, current_stmt, parent_stmts, global_special_stmts):
        self.link_parent_stmts_to_current_stmt(parent_stmts, current_stmt)
        last_stmts_of_then_body = [CFGNode(current_stmt, ControlFlowKind.IF_TRUE)]
        then_body_id = current_stmt.then_body
        if not util.isna(then_body_id):
            then_body = self.read_block(current_block, then_body_id)
            if len(then_body) != 0:
                last_stmts_of_then_body = self.analyze_block(then_body, last_stmts_of_then_body, global_special_stmts)
            
        last_stmts_of_else_body = [CFGNode(current_stmt, ControlFlowKind.IF_FALSE)]
        else_body_id = current_stmt.else_body
        if not util.isna(else_body_id):
            else_body = self.read_block(current_block, else_body_id)
            if len(else_body) != 0:
                last_stmts_of_else_body = self.analyze_block(else_body, last_stmts_of_else_body, global_special_stmts)

        boundary = self.boundary_of_multi_blocks(current_block, [then_body_id, else_body_id])
        return (last_stmts_of_then_body + last_stmts_of_else_body, boundary)

    def link_parent_stmts_to_current_stmt(self, parent_stmts: list, current_stmt):
        for node in parent_stmts:
            if isinstance(node, CFGNode):
                # Assumes node.stmt and node.edge are valid attributes for CFGNode
                self.cfg.add_edge(node.stmt, current_stmt, node.edge)
            else:
                # Links non-CFGNode items
                self.cfg.add_edge(node, current_stmt)

    def analyze_init_block(self, current_block, parent_stmts = [], special_stmts = []):
        counter = 0
        previous = parent_stmts
        last_parameter_decl_stmts = []
        last_parameter_init_stmts = []
        first_init_stmt = True

        if util.is_empty(current_block):
            return previous

        while counter < len(current_block):
            current = current_block.access(counter)
            if current.operation == "parameter_decl":
                self.link_parent_stmts_to_current_stmt(parent_stmts, current)
                last_parameter_init_stmts.extend(previous)
                last_parameter_decl_stmts.append(CFGNode(current, ControlFlowKind.PARAMETER_INPUT_TRUE))
                previous = [current]
                counter += 1
                first_init_stmt = True
            else:
                handler = self.stmt_handlers.get(current.operation)
                if first_init_stmt:
                    previous = [CFGNode(previous, ControlFlowKind.PARAMETER_INPUT_FALSE)]
                    first_init_stmt = False
                if handler is None:
                    self.link_parent_stmts_to_current_stmt(previous, current)
                    previous = [current]
                    counter += 1
                else:
                    previous, boundary = handler(current_block, current, previous, special_stmts)
                    if boundary < 0:
                        break
                    counter = boundary + 1
                if counter >= len(current_block):
                    last_parameter_init_stmts.extend(previous)

        return last_parameter_decl_stmts + last_parameter_init_stmts

    def analyze_block(self, current_block, parent_stmts = [], special_stmts = []):
        """
        This function is going to deal with current block and extract its control flow graph.
        It returns the last statements inside this block.
        """
        counter = 0
        boundary = 0
        previous = parent_stmts

        if util.is_empty(current_block):
            return previous

        while counter < len(current_block):
            current = current_block.access(counter)
            handler = self.stmt_handlers.get(current.operation)
            if handler is None:
                self.link_parent_stmts_to_current_stmt(previous, current)
                previous = [current]
                counter += 1
            else:
                previous, boundary = handler(current_block, current, previous, special_stmts)
                if boundary < 0:
                    break
                counter = boundary + 1

        return previous