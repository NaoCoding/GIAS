from pydantic import BaseModel
from typing import Optional


class AnalysisRequest(BaseModel):
    owner: str
    repo: str
    issue_id: int
    query: Optional[str] = None


class AnalysisResponse(BaseModel):
    issue_url: str
    issue_title: str
    issue_body: str
    analysis: str
    status: str


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    result: str
    status: str
