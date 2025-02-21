import asyncio
import logging
import os
from fastapi import HTTPException
from sqlalchemy.orm import Session
from typing import Any, Dict, Optional

from app.modules.projects.projects_service import ProjectService

logger = logging.getLogger(__name__)

class LocalRepoService:
    def __init__(self, db: Session):
        self.db = db
        self.project_manager = ProjectService(db)
        self.max_depth = 4  # Maximum recursion depth for folder scanning

    def get_repo(self, repo_path: str) -> str:
        """
        Validates that the local repository exists.
        """
        if not os.path.exists(repo_path):
            raise HTTPException(
                status_code=404, detail=f"Local repository at {repo_path} not found"
            )
        return repo_path

    def _build_directory_tree(
        self, current_path: str, current_depth: int, max_depth: int, base_dir: str
    ) -> Dict[str, Any]:
        """
        Recursively builds a tree representation of the directory.
        
        Args:
            current_path: Absolute path to the current folder.
            current_depth: Current recursion depth.
            max_depth: Maximum allowed depth.
            base_dir: The base repository directory (for computing relative paths).
        
        Returns:
            A dictionary representing the directory (or file) structure.
        """
        if current_depth >= max_depth:
            return {
                "type": "directory",
                "name": os.path.basename(current_path) or current_path,
                "children": [{"type": "file", "name": "...", "path": "truncated"}],
            }

        tree = {
            "type": "directory",
            "name": os.path.basename(current_path) or current_path,
            "children": []
        }
        try:
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)
                relative_path = os.path.relpath(item_path, base_dir)
                if os.path.isdir(item_path):
                    subtree = self._build_directory_tree(item_path, current_depth + 1, max_depth, base_dir)
                    tree["children"].append(subtree)
                else:
                    # Optionally, you could filter out certain file types here.
                    tree["children"].append({
                        "type": "file",
                        "name": item,
                        "path": relative_path
                    })
        except Exception as e:
            logger.error(f"Error listing directory {current_path}: {e}")
        return tree

    def _format_tree_structure(self, tree: Dict[str, Any], indent: int = 0) -> str:
        """
        Formats the directory tree as a string with indentation.
        """
        lines = []
        prefix = "  " * indent
        if tree["type"] == "directory":
            lines.append(f"{prefix}{tree['name']}/")
        else:
            lines.append(f"{prefix}{tree['name']}")
        for child in sorted(tree.get("children", []), key=lambda x: x["name"]):
            lines.append(self._format_tree_structure(child, indent + 1))
        return "\n".join(lines)

    async def get_project_structure_async(self, project_id: str, path: Optional[str] = None) -> str:
        """
        Asynchronously retrieves and parses the project structure.
        
        It uses the project manager to get the project details (which include the local repository path),
        then scans the repository (or subdirectory) and returns a formatted string.
        """
        # If your ProjectService does not provide an async version, run the synchronous call in an executor.
        loop = asyncio.get_running_loop()
        project = await loop.run_in_executor(None, self.project_manager.get_project_from_db_by_id_sync, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        repo_path = project.get("repo_path")
        if not repo_path:
            raise HTTPException(status_code=400, detail="Project has no associated local repository")

        # Verify the repository exists
        self.get_repo(repo_path)

        # Determine the starting directory
        start_path = os.path.join(repo_path, path) if path else repo_path
        tree = self._build_directory_tree(start_path, current_depth=0, max_depth=self.max_depth, base_dir=repo_path)
        formatted = self._format_tree_structure(tree)
        return formatted

    def get_file_content(
        self, repo_name: str, file_path: str, start_line: int, end_line: int,
        branch_name: str, project_id: str
    ) -> str:
        """
        Reads the file content from a local repository.
        (Note: Branch checkout is not implemented here for simplicity.)
        """
        logger.info(f"Accessing file: {file_path} for project ID: {project_id}")
        project = self.project_manager.get_project_from_db_by_id_sync(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        repo_path = project.get("repo_path")
        if not repo_path:
            raise HTTPException(status_code=400, detail="Project has no associated local repository")
        file_full_path = os.path.join(repo_path, file_path)
        if not os.path.exists(file_full_path):
            raise HTTPException(status_code=404, detail=f"File {file_path} not found in repository")
        try:
            with open(file_full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                # If start_line and end_line are not provided (or equal), return full file.
                if not start_line or start_line == end_line:
                    return "".join(lines)
                start = max(start_line - 1, 0)
                end = end_line if end_line <= len(lines) else len(lines)
                return "".join(lines[start:end])
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error processing file content: {str(e)}")
