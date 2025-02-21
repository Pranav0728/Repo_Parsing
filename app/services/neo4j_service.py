from neo4j import GraphDatabase
from app.core.config_provider import get_neo4j_config

neo4j_config = get_neo4j_config()
driver = GraphDatabase.driver(
    neo4j_config["uri"],
    auth=(neo4j_config["username"], neo4j_config["password"]),
)

def insert_repo_structure(parsed_data: dict):
    """
    Inserts repository data into Neo4j using keys from parsed_data:
      - repo_info: a string containing repository details (e.g., "Repository: CodexAi/frontend...")
      - directory_structure: a string representing the directory tree.
      - repo_code: a string containing code from multiple files, where individual files are 
                   separated by lines of "================================================"
    
    Returns a dictionary with the repository node's element id.
    """
    repo_info = parsed_data.get("repo_info", "")
    directory_structure = parsed_data.get("directory_structure", "")
    repo_code = parsed_data.get("repo_code", "")
    
    # Extract repository name from repo_info.
    repo_name = "Unknown"
    lines = repo_info.splitlines()
    if lines and lines[0].startswith("Repository:"):
        repo_name = lines[0].replace("Repository:", "").strip()
    
    # Parse repo_code into individual file entries.
    files = []
    delimiter = "================================================"
    blocks = repo_code.split(delimiter)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        # Expect each block to start with "File: <filename>"
        if block.startswith("File:"):
            parts = block.split("\n", 1)
            if len(parts) == 2:
                header, code = parts
                filename = header.replace("File:", "").strip()
                files.append({
                    "name": filename,
                    "code": code.strip(),
                    "path": filename  # Adjust this if you have a different path structure.
                })
    
    # Use a session with explicit write transactions.
    with driver.session() as session:
        # Create or update the Repository node and return it.
        def create_repository(tx, name, info, directory_structure, blocks):
            query = """
            MERGE (r:Repository {name: $name})
            SET r.info = $info, r.directory_structure = $directory_structure, r.blocks = $blocks
            RETURN r
            """
            result = tx.run(
                query,
                name=name,
                info=info,
                directory_structure=directory_structure,
                blocks=blocks
            )
            record = result.single()
            return record["r"] if record is not None else None

        repo_node = session.write_transaction(
            create_repository, repo_name, repo_info, directory_structure, blocks
        )
        
        # For each file, create (or update) the File node and link it to the repository.
        for file in files:
            session.write_transaction(
                lambda tx: tx.run(
                    """
                    MERGE (f:File {name: $name, path: $path})
                    ON CREATE SET f.code = $code
                    ON MATCH SET f.code = $code
                    WITH f
                    MATCH (r:Repository {name: $repo_name})
                    MERGE (r)-[:CONTAINS]->(f)
                    """,
                    name=file["name"],
                    path=file["path"],
                    code=file["code"],
                    repo_name=repo_name
                )
            )
        
        # Return the repository node's element id.
        if repo_node:
            # Prefer element_id if available (Bolt 4+); fallback to internal id.
            repo_id = repo_node.element_id if hasattr(repo_node, "element_id") else repo_node.id
            return {"repo_id": repo_id}
        else:
            return {"repo_id": None}
