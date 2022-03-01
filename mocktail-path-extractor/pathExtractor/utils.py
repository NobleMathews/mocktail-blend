import re


def normalizeAst(ast, graph_name, postOrder, splitToken=False, separator='|', labelPlaceholder='<SELF>',
                 useParentheses=True):
    label = separator.join(splitToSubtokens(graph_name))

    for currentNode in postOrder:
        attributes = normalizeNode(ast, graph_name, currentNode, splitToken, separator, labelPlaceholder,
                                   useParentheses)

    return label


def normalizeNode(graph, graph_name, node, splitToken=False, separator='|', labelPlaceholder='<SELF>',
                  useParentheses=True):
    checkers = list(graph.nodes(data="label"))
    checker = [item[1] for item in checkers if item[0] == node][0]
    attributes = str(checker)[2:-2].split(',')
    attributes = [attr.strip() for attr in attributes]

    if len(attributes) > 1:
        # Remove the method label from the tree
        if attributes[0] == 'METHOD' and attributes[1] == graph_name:  # Main method definition node.
            attributes[1] = labelPlaceholder

        elif attributes[0] == graph_name:  # Recursive call to itself.
            attributes[0] = labelPlaceholder
            attributes[1] = labelPlaceholder

        # Normalize the type label
        if useParentheses and not (attributes[0][0] == '(' and attributes[0][-1] == ')'):
            attributes[0] = '(' + attributes[0] + ')'

        # Normalize the token
        if splitToken:
            attributes[1] = separator.join(splitToSubtokens(attributes[1]))
        else:
            attributes[1] = normalizeToken(attributes[1])

        graph.nodes[node]['label'] = '"(' + ",".join(attributes) + ')"'

    return attributes


# This implementation is inspired by code2vec and astminer (https://github.com/JetBrains-Research/astminer).
def normalizeToken(token, defaultToken=""):
    cleanToken = token.lower()
    cleanToken = re.sub("\s+", "", cleanToken)  # escaped new line, whitespaces
    cleanToken = re.sub("[\"',]", "", cleanToken)  # quotes, apostrophies, commas
    cleanToken = re.sub("P{Print}", "", cleanToken)  # unicode weird characters

    stripped = re.sub("[^A-Za-z]", "", cleanToken)

    if not stripped:  # stripped is empty
        carefulStripped = re.sub(" ", "_", cleanToken)
        if not carefulStripped:  # carefulStripped is empty
            return defaultToken
        else:
            return carefulStripped

    return stripped


# This implementation is inspired by code2vec and astminer (https://github.com/JetBrains-Research/astminer).
def splitToSubtokens(token):
    token = token.strip()
    tokens = re.compile("(?<=[a-z])(?=[A-Z])|_|[0-9]|(?<=[A-Z])(?=[A-Z][a-z])|\\s+").split(token)
    normalizedTokens = map(lambda x: normalizeToken(x), tokens)
    normalizedTokens = list(filter(lambda x: x, normalizedTokens))

    return normalizedTokens


def toPathContext(ast, upPiece, topNode, downPiece, upSymbol='↑', downSymbol='↓'):
    # Creating upPath (list of type labels) from upPiece (list of ids) 
    upPath = []
    for index, currentNode in enumerate(upPiece):
        attributes = ast.nodes[currentNode]['label'][2:-2].split(',')
        attributes = [attr.strip() for attr in attributes]
        upPath.append(attributes[0])

        if index == 0:
            startToken = attributes[1]

    # Creating downPath (list of type labels) from downPiece (list of ids) 
    downPath = []
    for index, currentNode in enumerate(downPiece):
        attributes = ast.nodes[currentNode]['label'][2:-2].split(',')
        attributes = [attr.strip() for attr in attributes]
        downPath.append(attributes[0])

        if index == 0:
            endToken = attributes[1]

    # Exxtracting topNode's label using its id. 
    attributes = ast.nodes[topNode]['label'][2:-2].split(',')
    attributes = [attr.strip() for attr in attributes]
    topNode = attributes[0]

    # Creating pathContext from the path using (upPath, topNode, downPath). Also, adds arrows to store in file.
    upOrientedPath = ''.join([node + upSymbol for node in upPath])
    downOrientedPath = ''.join([downSymbol + node for node in downPath[::-1]])
    orientedPath = upOrientedPath + topNode + downOrientedPath

    return startToken, orientedPath, endToken
