import ast
import operator

def calculate(expression: str) -> str:
    """
    计算数学表达式，支持 + - * / ** 等
    """
    allowed_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
    }
    def eval_expr(node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = eval_expr(node.left)
            right = eval_expr(node.right)
            return allowed_operators[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = eval_expr(node.operand)
            return allowed_operators[type(node.op)](operand)
        else:
            raise TypeError(f"Unsupported operation: {type(node).__name__}")
    try:
        tree = ast.parse(expression, mode='eval')
        result = eval_expr(tree.body)
        return f"{expression} = {result}"
    except Exception as e:
        return f"计算错误: {e}"