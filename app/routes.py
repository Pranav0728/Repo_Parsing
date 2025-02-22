import asyncio
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db_session
from gitingest import ingest_async
from app.tools.get_code_file_structure_tool import RepoStructureRequest
from app.services.neo4j_service import insert_repo_structure

router = APIRouter()

@router.post("/repo/parse")
async def parse_github_repo(request: RepoStructureRequest, db: Session = Depends(get_db_session)):
    try:
        print("Received request:", request)

        summary, directory_structure, additional_data = await ingest_async(request.path)

        # print("Repository Summary:", summary)
        # print("Directory Structure:", directory_structure)
        # print("Additional Data:", additional_data)

        if not directory_structure.strip():
            raise HTTPException(
                status_code=500,
                detail="Empty directory structure received from ingest_async."
            )

        repo_data = {
            "repo_info": summary.strip(),
            "directory_structure": directory_structure.strip(),
            "repo_code": additional_data.strip()
        }
        # print("Structured Repository Data:", repo_data)

        # Insert into Neo4j and capture the returned repository id.
        result = insert_repo_structure(repo_data)
        # print("Neo4j Insertion Result:", result)

        return {
            "status": "success",
            "message": "Repository structure parsed and stored in Neo4j.",
            "neo4j_repo": result
        }
    except Exception as e:
        print("Error encountered:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
