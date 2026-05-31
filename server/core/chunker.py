from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from constants import EXTENSION_TO_LANGUAGE, CHUNK_NODE_TYPES, MAX_CHUNK_LINES

def get_parser(language_name: str) -> Parser:
    language = get_language(language_name)  
    parser = Parser(language)               
    return parser


def get_chunks_from_node(node, lines: list, path: str, chunk_node_types: set, max_lines: int = MAX_CHUNK_LINES) -> list:
    chunks = []

    if node.type in chunk_node_types:
        start_line = node.start_point[0]
        end_line = node.end_point[0]

        if end_line - start_line > max_lines:
            for child in node.children:
                chunks.extend(get_chunks_from_node(child, lines, path, chunk_node_types, max_lines))
        else:
            chunk_lines = lines[start_line:end_line + 1]
            chunks.append({
                "path": path,
                "start_line": start_line + 1,
                "end_line": end_line + 1,
                "content": "\n".join(chunk_lines),
            })
        return chunks

    for child in node.children:
        chunks.extend(get_chunks_from_node(child, lines, path, chunk_node_types, max_lines))

    return chunks


def fallback_line_chunks(path: str, lines: list, max_lines: int = MAX_CHUNK_LINES) -> list:
    return [
        {
            "path": path,
            "start_line": i + 1,
            "end_line": min(i + max_lines, len(lines)),
            "content": "\n".join(lines[i:i + max_lines]),
        }
        for i in range(0, len(lines), max_lines)
    ]


def chunk_file(path: str, content: str, max_lines: int = MAX_CHUNK_LINES) -> list:
    ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""
    language_name = EXTENSION_TO_LANGUAGE.get(ext)
    lines = content.split("\n")

    if not language_name:
        return fallback_line_chunks(path, lines, max_lines)

    try:
        parser = get_parser(language_name)
        tree = parser.parse(bytes(content, "utf-8"))
        chunk_node_types = CHUNK_NODE_TYPES.get(language_name, set())
        chunks = get_chunks_from_node(tree.root_node, lines, path, chunk_node_types, max_lines)

        return chunks if chunks else fallback_line_chunks(path, lines, max_lines)

    except Exception as e:
        print(f"[chunker] tree-sitter failed for {path}: {e}, falling back to line chunks")
        return fallback_line_chunks(path, lines, max_lines)


def chunk_all_files(files: list) -> list:
    all_chunks = []
    for file in files:
        chunks = chunk_file(file["path"], file["content"])
        all_chunks.extend(chunks)
    return all_chunks