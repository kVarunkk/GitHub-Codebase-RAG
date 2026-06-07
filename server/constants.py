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
BLOCKED_DIRS = {
    # dependency folders
    "node_modules",
    "vendor",
    "venv",
    ".venv",
    "env",
    ".env",
    "site-packages",

    # build output
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    ".output",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",

    # generated/compiled
    "generated",
    ".generated",
    "migrations",   # DB migrations — repetitive SQL, not useful for QA
    "coverage",
    ".nyc_output",

    # assets — not code
    "public",
    "static",
    "assets",
    "images",
    "fonts",
    "icons",
    "media",

    # docs build output
    "_next",
    "_site",
    "docs/_build",

    # git/ide
    ".git",
    ".github",
    ".vscode",
    ".idea",

    # mobile
    "android",
    "ios",
    "Pods",

    # infra — not useful for code QA
    "terraform",
    ".terraform",
}
BLOCKED_FILE_PATTERNS = {
    ".min.js",
    ".min.css",
    ".bundle.js",
    ".chunk.js",
    ".map",
    ".lock",
    ".generated.",
    "-lock.json",    # package-lock.json, yarn-lock.json
    ".snap",         # jest snapshots
    "_pb2.py",       # protobuf generated
    ".pb.go",        # protobuf generated go
}
COLLECTION_NAME = "GH-RAG-APP"
VECTOR_DIM = 384
MAX_CHUNK_LINES = 60
GEMINI_MODEL = "gemini-2.5-flash"