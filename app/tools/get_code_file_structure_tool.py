import asyncio
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.modules.code_provider.code_provider_service import CodeProviderService


class RepoStructureRequest(BaseModel):
    path: Optional[str] = None