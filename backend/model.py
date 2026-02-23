from typing import Optional, List

from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    owner: str
    repo: str
    issue_id: int
    query: Optional[str] = None


class PatchInfo(BaseModel):
    """Information about generated patch"""
    patch_file: Optional[str] = None
    patch_content: Optional[str] = None
    metadata_file: Optional[str] = None
    commit_message: Optional[str] = None
    files_changed: List[str] = []
    status: str = "not_generated"  # not_generated, success, failed, warning


class AnalysisResponse(BaseModel):
    issue_url: str
    issue_title: str
    issue_body: str
    analysis: str
    status: str
    patch: Optional[PatchInfo] = None  # NEW: Include patch info


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    result: str
    status: str
    patch: Optional[PatchInfo] = None  # NEW: Include patch info


class PatchGenerationRequest(BaseModel):
    """Request to generate a patch from an issue analysis"""
    owner: str
    repo: str
    issue_id: int
    issue_title: str
    issue_body: str
    analysis: str
    query: Optional[str] = None


class PatchGenerationResponse(BaseModel):
    """Response containing generated patch information"""
    status: str
    issue_id: int
    issue_title: str
    patch_file: Optional[str] = None
    metadata_file: Optional[str] = None
    commit_message: Optional[str] = None
    files_changed: List[str] = []
    specification: str = ""
    message: Optional[str] = None


class RAGBuildRequest(BaseModel):
    """Request to build RAG knowledge base"""
    owner: str
    repo: str
    save_code: bool = True  # Whether to save repository code to disk


class RAGBuildResponse(BaseModel):
    """Response from RAG building"""
    status: str
    message: str
    document_count: int
    saved_repo_path: Optional[str] = None


class PatchListResponse(BaseModel):
    """Response containing list of generated patches"""
    status: str
    patches: List[dict] = []
    total_count: int = 0
