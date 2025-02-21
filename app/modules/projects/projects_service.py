# app/modules/projects/projects_service.py

class ProjectService:
    def __init__(self, db):
        self.db = db

    def get_project_from_db_by_id_sync(self, project_id: str):
        """
        Synchronous method to fetch a project record from the database.
        For demonstration purposes, this returns a dummy record.
        In a real application, you'd query your database for the project.
        """
        # Dummy project record. Adjust the repo_path to point to a valid local repository.
        return {
            "id": project_id,
            "repo_path": "/Users/pranavmolawade/Documents/Tellis/CodexAi/frontend",  
            "repo_name": "my-repo",
            "branch_name": "main"
        }

    async def get_project_from_db_by_id(self, project_id: str):
        """
        Asynchronous method to fetch a project record.
        This simply wraps the synchronous method in an async function.
        """
        # In production, use an async DB driver (like asyncpg) and proper async queries.
        return self.get_project_from_db_by_id_sync(project_id)
