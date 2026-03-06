# ============================================================
# Error handling: Exception types for Mryl compiler
# ============================================================

class MrylError(Exception):
    """Base exception for Mryl compiler"""
    pass

class TypeError_(MrylError):
    """Type checking error with AST node information"""
    def __init__(self, message, node=None):
        super().__init__(message)
        self.node = node

class SyntaxError_(MrylError):
    """Syntax error with token information"""
    def __init__(self, message, token=None):
        super().__init__(message)
        self.token = token

class RuntimeError_(MrylError):
    """Runtime error (e.g. division by zero, index out of bounds)"""
    def __init__(self, message, node=None):
        super().__init__(message)
        self.node = node