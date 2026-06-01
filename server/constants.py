EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
}
CHUNK_NODE_TYPES = {
    "python": {"function_definition", "class_definition"},
    "typescript": {"function_declaration", "method_definition", "class_declaration", "arrow_function", "export_statement"},
    "tsx": {"function_declaration", "method_definition", "class_declaration", "arrow_function", "export_statement"},
    "javascript": {"function_declaration", "method_definition", "class_declaration", "arrow_function"},
    "jsx": {"function_declaration", "method_definition", "class_declaration", "arrow_function"},
    "go": {"function_declaration", "method_declaration"},
    "rust": {"function_item", "impl_item"},
    "java": {"method_declaration", "class_declaration"},
}
CODE_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx",
    ".java", ".c", ".cpp", ".go", ".rs",
    ".rb", ".php", ".swift", ".kt", ".cs"
}
COLLECTION_NAME = "GH-RAG-APP"
VECTOR_DIM = 384
MAX_CHUNK_LINES = 60
GEMINI_MODEL = "gemini-2.5-flash"