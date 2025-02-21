import os
from typing import Optional

# Import your local repository service
from app.modules.code_provider.local_repo.local_repo_service import LocalRepoService
# Optionally, you might have a GitHub-based service for production use:
# from app.modules.code_provider.github.github_service import GithubService

class CodeProviderService:
    def __init__(self, db):
        self.db = db
        self.service_instance = self._get_service_instance()

    def _get_service_instance(self):
        # Use LocalRepoService if in development mode; otherwise, use the GitHub-based service.
        if os.getenv("isDevelopmentMode", "enabled") == "enabled":
            return LocalRepoService(self.db)
        else:
            # Uncomment and use your GitHub service when available.
            # return GithubService(self.db)
            return LocalRepoService(self.db)

    async def get_project_structure_async(self, project_id: str, path: Optional[str] = None) -> str:
        return await self.service_instance.get_project_structure_async(project_id, path)

    def get_file_content(
        self, repo_name: str, file_path: str, start_line: int, end_line: int,
        branch_name: str, project_id: str
    ) -> str:
        return self.service_instance.get_file_content(repo_name, file_path, start_line, end_line, branch_name, project_id)
