import networkx as nx
from pathExtractor.utils import *
import os
from timeit import default_timer as timer

timeout_duration = 120.0
max_length = 100
max_child = 50


def extract_ast_paths(ast_path, graph_name, maxLength=8, maxWidth=2, maxTreeSize=200, splitToken=False, separator='|', upSymbol='↑',
                      downSymbol='↓', labelPlaceholder='<SELF>', useParentheses=True):
    start = timer()
    try:
        ast = nx.DiGraph(nx.drawing.nx_pydot.read_dot(ast_path))
    except:
        return "", []

    if ast.number_of_nodes() > maxTreeSize or ast.number_of_nodes() == 0:
        return "", []

    nx.set_node_attributes(ast, [], 'pathPieces')

    # source = "1000101" if "1000101" in ast else min(ast.nodes)
    source_nodes = [node for node, indegree in ast.in_degree(ast.nodes()) if indegree == 0]
    for node_id in source_nodes:
        if "(METHOD" in (ast._node[node_id]['label']):
            continue
        else:
            source_nodes.remove(node_id)

    # if len(source_nodes)>0:
    #     source = source_nodes[0]

    paths = []
    for source in source_nodes:
        postOrder = list(nx.dfs_postorder_nodes(ast, source=source))

        normalizedLabel = normalizeAst(ast, graph_name, postOrder, splitToken, separator, labelPlaceholder, useParentheses)
        for currentNode in postOrder:
            if timer() - start > timeout_duration:
                return "", []
            if not list(ast.successors(currentNode)):  # List is empty i.e node is leaf
                attributes = ast.nodes[currentNode]['label'][2:-2].split(',')
                attributes = [attr.strip() for attr in attributes]
                if len(attributes) > 1 and attributes[1]:  # attribute[1] is token of the leaf node. If the token is not empty.
                    ast.nodes[currentNode]['pathPieces'] = [[currentNode]]
            else:
                # Creates a list of pathPieces per child i.e. list(list(list(nodes))) <--> list(list(pathPieces)) <--> list(PathPieces per child)
                pathPiecesPerChild = list(map(lambda x: ast.nodes[x]['pathPieces'], list(ast.successors(currentNode))))

                # Append current node to all the pathPieces. And flatten the list(list(pathPieces)) to list(pathPieces).
                currentNodePathPieces = [pathPiece + [currentNode] for pathPieceList in pathPiecesPerChild for pathPiece
                                         in pathPieceList if maxLength == None or len(pathPiece) <= maxLength]
                ast.nodes[currentNode]['pathPieces'] = currentNodePathPieces

                # Find list of paths that pass through the current node (leaf -> currentNode -> leaf). Also, filter as per maxWidth and maxLength
                for index, leftChildsPieces in enumerate(pathPiecesPerChild):
                    if maxWidth is None:
                        maxIndex = len(pathPiecesPerChild)
                    else:
                        maxIndex = min(index + maxWidth + 1, len(pathPiecesPerChild))

                    for rightChildsPieces in pathPiecesPerChild[index + 1: maxIndex]:
                        for upPiece in leftChildsPieces:
                            for downPiece in rightChildsPieces:
                                if ((maxLength == None) or (len(upPiece) + 1 + len(downPiece) <= maxLength)):
                                    paths.append(
                                        toPathContext(ast, upPiece, currentNode, downPiece, upSymbol, downSymbol))

    # print('\n')
    # for path in paths:
    #     print(path)

    return normalizedLabel, paths


def extract_cfg_paths(cfg_path, graph_name,  source_nodes, splitToken=False, separator='|', upSymbol='↑', downSymbol='↓',
                      labelPlaceholder='<SELF>', useParentheses=True):
    try:
        cfg = nx.DiGraph(nx.drawing.nx_pydot.read_dot(cfg_path))
        # selected_nodes = []
        # for source in source_nodes:
        #     if source in cfg.nodes():
        #         selected_nodes.append(source)
        # if not selected_nodes:
        #     selected_nodes.append(min(cfg.nodes))
        source = min(cfg.nodes)

    except:
        return []

    paths = []
    Visited = []
    # for source in selected_nodes:
    start = timer()
    paths.extend(
        traverse_cfg_paths(start, cfg, graph_name, source, paths.copy(), Visited.copy(), "", splitToken, separator, upSymbol,
                           downSymbol, labelPlaceholder, useParentheses))

    # print('\ncfg:')
    # for path in paths:
    #     print(path)

    return paths


def traverse_cfg_paths(start, cfg, graph_name, node, path, Visited, start_token="", splitToken=False, separator='|', upSymbol='↑',
                       downSymbol='↓', labelPlaceholder='<SELF>', useParentheses=True):
    attributes = normalizeNode(cfg, graph_name, node, splitToken, separator, labelPlaceholder, useParentheses)
    if path:
        path.append(downSymbol + attributes[0])
    else:
        path.append(attributes[0])
        start_token = attributes[1]

    Visited.append(node)

    if timer() - start > timeout_duration or len(path) > max_length:
        return [(start_token, ''.join(path), attributes[1])]

    children = list(cfg.successors(node))
    child_paths = []

    if children:
        for child in children:
            if child not in Visited and len(child_paths) < max_child:
                child_paths += traverse_cfg_paths(start, cfg, graph_name, child, path.copy(), Visited.copy(), start_token,
                                                  splitToken,
                                                  separator, upSymbol, downSymbol, labelPlaceholder, useParentheses)
            else:
                attributes = normalizeNode(cfg, graph_name, child, splitToken, separator, labelPlaceholder, useParentheses)
                child_paths.append((start_token, ''.join(path + [upSymbol + attributes[0]]), attributes[1]))
    else:
        return [(start_token, ''.join(path), attributes[1])]

    return child_paths


def extract_cdg_paths(cdg_path, graph_name, splitToken=False, separator='|', upSymbol='↑', downSymbol='↓',
                      labelPlaceholder='<SELF>', useParentheses=True):
    try:
        cdg = nx.DiGraph(nx.drawing.nx_pydot.read_dot(cdg_path))
        root = min(cdg.nodes)
    except:
        return []

    if nx.is_empty(cdg):
        return []

    # Removing self-loops and finding the root of the CDG (which is a tree, if self-loops are removed).
    # cdg.remove_edges_from(nx.selfloop_edges(cdg))
    # root = [node for node, degree in cdg.in_degree() if degree == 0]
    paths = []
    Visited = []
    start = timer()
    paths = traverse_cdg_paths(start, cdg, graph_name, root, paths, Visited, "", splitToken, separator, upSymbol, downSymbol,
                               labelPlaceholder, useParentheses)

    # print("\ncdg:")
    # for path in paths:
    #     print(path)

    return paths


def traverse_cdg_paths(start, cdg, graph_name, node, path, Visited, start_token="", splitToken=False, separator='|', upSymbol='↑',
                       downSymbol='↓', labelPlaceholder='<SELF>', useParentheses=True):
    attributes = normalizeNode(cdg, graph_name, node, splitToken, separator, labelPlaceholder, useParentheses)
    if path:
        path.append(downSymbol + attributes[0])
    else:
        path.append(attributes[0])
        start_token = attributes[1]

    Visited.append(node)
    if timer() - start > timeout_duration or len(path) > max_length:
        return [(start_token, ''.join(path), attributes[1])]
    children = list(cdg.successors(node))
    child_paths = []

    if children:
        for child in children:
            if child not in Visited and len(child_paths) < max_child:
                child_paths += traverse_cdg_paths(start, cdg, graph_name, child, path.copy(), Visited.copy(), start_token,
                                                  splitToken,
                                                  separator, upSymbol, downSymbol, labelPlaceholder, useParentheses)
            else:
                attributes = normalizeNode(cdg, graph_name, child, splitToken, separator, labelPlaceholder, useParentheses)
                child_paths.append((start_token, ''.join(path + [upSymbol + attributes[0]]), attributes[1]))
    else:
        return [(start_token, ''.join(path), attributes[1])]

    return child_paths


def extract_ddg_paths(ddg_path, graph_name,  source="1000101", splitToken=False, separator='|', upSymbol='↑', downSymbol='↓',
                      labelPlaceholder='<SELF>', useParentheses=True):
    try:
        ddg = nx.MultiDiGraph(nx.drawing.nx_pydot.read_dot(ddg_path))
        source = min(ddg.nodes)
    except:
        return []

    paths = []
    Visited = []
    start = timer()
    paths = traverse_ddg_paths(start, ddg, graph_name, source, paths.copy(), Visited.copy(), "", "", splitToken, separator,
                               upSymbol,
                               downSymbol, labelPlaceholder, useParentheses)
    paths = list(set([path for path in paths]))

    # print('\nddg:')
    # for path in paths:
    #     print(path)

    return paths


def traverse_ddg_paths(start, ddg, graph_name, node, path, Visited, start_token="", edge_label="", splitToken=False, separator='|',
                       upSymbol='↑', downSymbol='↓', labelPlaceholder='<SELF>', useParentheses=True):
    attributes = normalizeNode(ddg, graph_name, node, splitToken, separator, labelPlaceholder, useParentheses)
    if path:
        path.append(downSymbol + attributes[0])
    else:
        path.append(attributes[0])
        start_token = attributes[1]

    Visited.append(node)
    edges = ddg.edges(node, data='label')
    child_paths = []

    if timer() - start > timeout_duration or len(path) > max_length:
        return [(start_token, ''.join(path), attributes[1])]

    if edges:
        for edge in edges:
            if edge_label == "" or edge_label == None or edge_label in edge[2] or edge[2] in edge_label:
                if edge[1] not in Visited  and len(child_paths) < max_child:
                    if edge_label == "" or edge_label == None or edge[2] in edge_label:
                        child_paths += traverse_ddg_paths(start, ddg, graph_name, edge[1], path.copy(), Visited.copy(), start_token,
                                                          edge[2], splitToken, separator, upSymbol, downSymbol,
                                                          labelPlaceholder, useParentheses)
                    elif edge_label in edge[2]:
                        child_paths += traverse_ddg_paths(start, ddg, graph_name, edge[1], path.copy(), Visited.copy(), start_token,
                                                          edge_label, splitToken, separator, upSymbol, downSymbol,
                                                          labelPlaceholder, useParentheses)
                else:
                    attributes = normalizeNode(ddg, graph_name, edge[1], splitToken, separator, labelPlaceholder, useParentheses)
                    child_paths.append((start_token, ''.join(path + [upSymbol + attributes[0]]), attributes[1]))
    else:
        return [(start_token, ''.join(path), attributes[1])]

    return child_paths
