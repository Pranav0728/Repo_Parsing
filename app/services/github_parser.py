import asyncio
from sqlalchemy.orm import Session
from app.tools.get_code_file_structure_tool import get_code_file_structure_tool, RepoStructureRequest

async def get_repo_structure(request: RepoStructureRequest, db: Session) -> str:
    """
    Uses GetCodeFileStructureTool to fetch the repository structure asynchronously.
    This returns an indented textual representation of the repository's tree.
    """
    tool = get_code_file_structure_tool(db)
    return await tool.coroutine(project_id=request.project_id, path=request.path)

def parse_file_structure(structure_str: str) -> dict:
    """
    Parse an indented textual file structure into a dictionary mapping to your graph model.

    Expected format example:
        Sample/
          src/
            main.js
          README.md

    - The first non-empty line is taken as the repository name.
    - Directories end with a "/" character.
    - Each indent level is represented by two spaces.
    
    Returns a dictionary with keys:
      - repository: { name, url }
      - files: list of file nodes { name, path }
      - directories: list of directory nodes { name, path }
      - relationships: list of relationships { from, to }
    """
    lines = [line for line in structure_str.splitlines() if line.strip()]
    if not lines:
        raise ValueError("Empty structure string")

    files = []
    directories = []
    relationships = []
    stack = []  # Each element: (indent level, node_dict)

    # The first line is the repository name.
    repo_line = lines[0].strip()
    repository_name = repo_line.rstrip("/")
    repository = {"name": repository_name, "url": f"https://github.com/user/{repository_name}"}
    # Treat the repository as the root node.
    root_node = {"name": repository_name, "type": "repository", "path": repository_name}
    directories.append({"name": repository_name, "path": repository_name})
    stack.append((0, root_node))

    # Process the remaining lines.
    for line in lines[1:]:
        indent = len(line) - len(line.lstrip(" "))
        level = indent // 2  # Two spaces per indent level.
        node_name = line.strip()
        node_type = "directory" if node_name.endswith("/") else "file"
        if node_type == "directory":
            node_name = node_name.rstrip("/")
        # Pop from the stack until we find a node with a lower indent level.
        while stack and stack[-1][0] >= level:
            stack.pop()
        parent_node = stack[-1][1] if stack else root_node
        parent_path = parent_node["path"]
        current_path = f"{parent_path}/{node_name}" if parent_path else node_name
        node_dict = {"name": node_name, "type": node_type, "path": current_path}
        if node_type == "file":
            files.append({"name": node_name, "path": current_path})
        else:
            directories.append({"name": node_name, "path": current_path})
            stack.append((level, node_dict))
        relationships.append({
            "from": parent_path if parent_path else repository_name,
            "to": current_path
        })

    return {
        "repository": repository,
        "files": files,
        "directories": directories,
        "relationships": relationships
    }

def summarize_structure(parsed_data: dict) -> str:
    """
    Create a plain text summary of the parsed repository structure.
    """
    repo = parsed_data.get("repository", {})
    repo_name = repo.get("name", "Unknown Repo")
    files = parsed_data.get("files", [])
    directories = parsed_data.get("directories", [])
    summary = f"Repository: {repo_name}\n"
    summary += "Directories:\n" + "\n".join([f"  - {d['path']}" for d in directories]) + "\n"
    summary += "Files:\n" + "\n".join([f"  - {f['path']}" for f in files])
    return summary

async def get_structure_and_code(request: RepoStructureRequest, db: Session, branch_name: str) -> dict:
    """
    For a local repository, fetch the repository structure as an indented string,
    parse it into a dictionary, and enrich it with file contents.

    It uses the LocalRepoService to retrieve both structure and file content.
    Returns the enriched dictionary.
    """
    from app.modules.code_provider.local_repo.local_repo_service import LocalRepoService
    local_service = LocalRepoService(db)
    structure_str = await local_service.get_project_structure_async(request.project_id, request.path)
    parsed_data = parse_file_structure(structure_str)
    # Enrich each file node with code content.
    repo_name = parsed_data["repository"]["name"]
    # For demonstration, we use the project ID from the request.
    project_id = request.project_id
    for file_node in parsed_data.get("files", []):
        file_path = file_node["path"]
        try:
            content = local_service.get_file_content(
                repo_name,
                file_path,
                0, 0,  # Retrieve the entire file.
                branch_name,
                project_id
            )
            file_node["code"] = content
        except Exception as e:
            file_node["code"] = f"Error retrieving file: {str(e)}"
    parsed_data["file_contents"] = {fn["path"]: fn.get("code", "") for fn in parsed_data.get("files", [])}
    return parsed_data
