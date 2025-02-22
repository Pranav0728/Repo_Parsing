import os
from neo4j import GraphDatabase
from app.core.config_provider import get_neo4j_config

neo4j_config = get_neo4j_config()
driver = GraphDatabase.driver(
    neo4j_config["uri"],
    auth=(neo4j_config["username"], neo4j_config["password"]),
)

def insert_repo_structure(parsed_data: dict):
    print("Parsed Data:", parsed_data)
    """
    Inserts repository data into Neo4j.
    Expects parsed_data with keys:
      - repo_info: string (e.g., "Repository: CodexAi/frontend...")
      - directory_structure: a text tree of directories/files.
      - repo_code: a string containing code for multiple files, separated by
                   delimiter lines "================================================"
                   
    This function:
      1. Extracts the repository name.
      2. Builds a file-code mapping from repo_code.
      3. Parses the directory_structure into a tree.
      4. Creates a Repository node.
      5. Recursively creates Directory and File nodes (with parent–child CONTAINS relationships).
      6. Links the Repository node to its top-level directories.
      
    Returns a dict with the repository node's element id.
    """
    repo_info = parsed_data.get("repo_info", "")
    directory_structure_str = parsed_data.get("directory_structure", "")
    repo_code = parsed_data.get("repo_code", "")

    # Extract repository name (assumes first line is "Repository: <name>")
    repo_name = "Unknown"
    lines = repo_info.splitlines()
    if lines and lines[0].startswith("Repository:"):
        repo_name = lines[0].replace("Repository:", "").strip()

    # Build a mapping of file identifier to its code from repo_code.
    # Store using both the full header and the base name.
    file_code_mapping = {}
    delimiter = "================================================"
    blocks = repo_code.split(delimiter)
    i = 0
    while i < len(blocks):
        header_block = blocks[i].strip()
        if header_block.startswith("File:"):
            header_content = header_block.replace("File:", "").strip()  # may be full path like "src/app/page.jsx"
            base_filename = os.path.basename(header_content)
            code = ""
            if i + 1 < len(blocks):
                code = blocks[i + 1].strip()
            # Store code under both keys
            file_code_mapping[header_content] = code
            file_code_mapping[base_filename] = code
            i += 2  # Skip header and code block.
        else:
            i += 1

    print("blocks:", blocks)
    print("File Code Mapping:", file_code_mapping)

    # Parse the directory structure into a tree.
    def parse_directory_structure(structure_str):
        lines = structure_str.splitlines()
        tree_nodes = []
        stack = []
        for line in lines:
            if "──" not in line:
                continue
            # Determine indentation level (number of leading spaces)
            indent = len(line) - len(line.lstrip(" "))
            # Remove tree markers ("└──" or "├──") and extra spaces:
            name = line.split("──", 1)[1].strip()
            # Determine type: directory if name ends with '/', else file.
            node_type = "directory" if name.endswith("/") else "file"
            # Initialize the node; full_path will be updated based on hierarchy.
            node = {"name": name, "type": node_type, "children": [], "full_path": name}
            # Pop from stack until finding a parent with lower indent.
            while stack and stack[-1]["indent"] >= indent:
                stack.pop()
            if stack:
                parent_node = stack[-1]["node"]
                node["full_path"] = parent_node["full_path"] + "/" + name
                parent_node["children"].append(node)
            else:
                tree_nodes.append(node)
            # Push the current node with its indent onto the stack.
            stack.append({"node": node, "indent": indent})
        return tree_nodes

    tree = parse_directory_structure(directory_structure_str)

    with driver.session() as session:
        # Create or update the Repository node.
        def create_repository(tx, name, info, structure):
            query = """
            MERGE (r:Repository {name: $name})
            SET r.info = $info, r.directory_structure = $structure
            RETURN r
            """
            result = tx.run(query, name=name, info=info, structure=structure)
            record = result.single()
            return record["r"] if record is not None else None

        repo_node = session.write_transaction(create_repository, repo_name, repo_info, directory_structure_str)

        # Create a node for a given tree entry (Directory or File).
        def create_tree_node(tx, node):
            if node["type"] == "directory":
                query = """
                MERGE (d:Directory {full_path: $full_path})
                SET d.name = $name
                RETURN d
                """
                result = tx.run(query, full_path=node["full_path"], name=node["name"])
                record = result.single()
                return record["d"] if record is not None else None
            else:
                # For file nodes, attach the code if available.
                simple_name = node["name"]  # e.g., "page.jsx"
                # Try matching by full_path then by simple name.
                code = file_code_mapping.get(node["full_path"], file_code_mapping.get(simple_name, ""))
                query = """
                MERGE (f:File {full_path: $full_path})
                SET f.name = $name, f.code = $code
                RETURN f
                """
                result = tx.run(query, full_path=node["full_path"], name=node["name"], code=code)
                record = result.single()
                return record["f"] if record is not None else None

        # Recursively traverse the tree to create nodes and relationships.
        def traverse_tree(tx, node, parent_full_path=None):
            created_node = create_tree_node(tx, node)
            if parent_full_path:
                rel_query = """
                MATCH (parent {full_path: $parent_full_path}), (child {full_path: $child_full_path})
                MERGE (parent)-[:CONTAINS]->(child)
                """
                tx.run(rel_query, parent_full_path=parent_full_path, child_full_path=node["full_path"])
            for child in node.get("children", []):
                traverse_tree(tx, child, node["full_path"])
            return created_node

        for root_node in tree:
            session.write_transaction(traverse_tree, root_node)
            session.write_transaction(lambda tx: tx.run(
                """
                MATCH (r:Repository {name: $repo_name}), (d {full_path: $full_path})
                MERGE (r)-[:HAS_DIRECTORY]->(d)
                """,
                repo_name=repo_name,
                full_path=root_node["full_path"]
            ))

        if repo_node:
            repo_id = repo_node.element_id if hasattr(repo_node, "element_id") else repo_node.id
            return {"repo_id": repo_id}
        else:
            return {"repo_id": None}
