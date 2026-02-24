import asyncio
import logging
import os
import sys
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from pydantic import BaseModel

from agent.root_agent import root_agent
from agent.patch_agent import PatchAgent
from backend.model import (
    AnalysisRequest,
    AnalysisResponse,
    QueryRequest,
    QueryResponse,
    PatchInfo,
    PatchGenerationRequest,
    PatchGenerationResponse,
    RAGBuildRequest,
    RAGBuildResponse,
    PatchListResponse,
)
from tool.github_tool import get_issue_by_issue_id, get_repo_content_by_git
from tool.rag_tool import create_rag_knowledge_base

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_EMBEDDING_MODEL = "embeddinggemma"
OLLAMA_BASE_URL = "http://localhost:11434"
CHROMA_DB_PATH = "./chroma_db"
PATCHES_DIR = "./patches"
# Default repository for patch agent initialization
DEFAULT_REPO_OWNER = "psf"
DEFAULT_REPO_NAME = "requests"

# Initialize FastAPI app
app = FastAPI(title="GIAS Backend - GitHub Issue Analysis Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables
_agent = None
_vectorstore = None
_patch_agent = None
_current_repo_owner = DEFAULT_REPO_OWNER
_current_repo_name = DEFAULT_REPO_NAME


async def initialize_agent():
    """Initialize the root agent with vectorstore"""
    global _agent, _vectorstore

    try:
        logger.info("Initializing embeddings...")
        embeddings = OllamaEmbeddings(
            model=OLLAMA_EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL
        )

        logger.info(f"Loading vectorstore from {CHROMA_DB_PATH}...")
        _vectorstore = Chroma(
            persist_directory=CHROMA_DB_PATH, embedding_function=embeddings
        )

        logger.info("Initializing root agent...")
        _agent = root_agent(_vectorstore)
        logger.info("Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        raise


def _initialize_patch_agent():
    """Initialize patch agent for current repository"""
    global _patch_agent, _vectorstore, _current_repo_owner, _current_repo_name
    
    if _vectorstore and _current_repo_owner and _current_repo_name:
        _patch_agent = PatchAgent(
            _vectorstore,
            _current_repo_owner,
            _current_repo_name,
            patches_dir=PATCHES_DIR,
        )
        logger.info(f"Patch agent initialized for {_current_repo_owner}/{_current_repo_name}")


def _generate_patch_internal(
    owner: str,
    repo: str,
    issue_id: int,
    issue_title: str,
    issue_body: str,
    analysis: str,
) -> PatchInfo:
    """
    Internal helper to generate a patch and return PatchInfo.
    This is called automatically after analysis.
    
    Args:
        owner: Repository owner
        repo: Repository name
        issue_id: GitHub issue ID
        issue_title: Issue title
        issue_body: Issue description
        analysis: AI analysis result
        
    Returns:
        PatchInfo object with patch details or empty if generation failed
    """
    try:
        # Only generate patch if patch agent is initialized and repo matches
        if not _patch_agent:
            logger.warning(
                f"⚠️  Patch agent not initialized. "
                f"Please call /api/build-rag with owner='{owner}' and repo='{repo}' first to enable patch generation."
            )
            return PatchInfo(status="not_generated")
        
        if _current_repo_owner != owner or _current_repo_name != repo:
            logger.warning(
                f"⚠️  Repository mismatch for patch generation. "
                f"Expected: {_current_repo_owner}/{_current_repo_name}, "
                f"Got: {owner}/{repo}. "
                f"Please call /api/build-rag for {owner}/{repo} to generate patches for this repository."
            )
            return PatchInfo(status="not_generated")
        
        logger.info(f"Auto-generating patch for issue #{issue_id}...")
        
        # Generate the patch
        result = _patch_agent.generate_patch(
            issue_id=issue_id,
            issue_title=issue_title,
            issue_body=issue_body,
            analysis=analysis,
        )
        
        if result["status"] == "success":
            # Read patch content to send to frontend
            patch_content = None
            patch_file = result.get("patch_file")
            if patch_file and os.path.exists(patch_file):
                try:
                    with open(patch_file, "r", encoding="utf-8") as f:
                        patch_content = f.read()
                except Exception as e:
                    logger.warning(f"Could not read patch file: {e}")
            
            return PatchInfo(
                patch_file=patch_file,
                patch_content=patch_content,
                metadata_file=result.get("metadata_file"),
                commit_message=result.get("commit_message"),
                files_changed=result.get("files_changed", []),
                status="success",
            )
        elif result["status"] == "warning":
            return PatchInfo(
                patch_content=result.get("specification", ""),
                status="warning",
            )
        else:
            logger.warning(f"Patch generation failed: {result.get('message')}")
            return PatchInfo(status="failed")
            
    except Exception as e:
        logger.warning(f"Error during auto patch generation: {e}")
        return PatchInfo(status="failed")


@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup"""
    await initialize_agent()

    # Initialize patch agent with default repository
    _initialize_patch_agent()

# API Routes
@app.get("/")
async def read_root():
    """Serve the frontend HTML"""
    return FileResponse("server/frontend.html")


@app.post("/api/analyze-issue", response_model=AnalysisResponse)
async def analyze_issue(request: AnalysisRequest):
    """
    Analyze a GitHub issue using RAG and root agent.
    Automatically generates a patch from the analysis.

    Args:
        owner: Repository owner
        repo: Repository name
        issue_id: GitHub issue ID
        query: Optional custom query (if not provided, uses issue content)
    """
    try:
        if _agent is None:
            raise HTTPException(
                status_code=503,
                detail="Agent not initialized. Please check Ollama and database connection.",
            )

        logger.info(
            f"Analyzing issue: {request.owner}/{request.repo}#{request.issue_id}"
        )

        # Fetch issue from GitHub
        try:
            issue = get_issue_by_issue_id(
                f"{request.owner}/{request.repo}", request.issue_id
            )
            issue_title = issue.title
            issue_body = issue.body or "No description provided"
            issue_url = issue.html_url
        except Exception as e:
            logger.error(f"Failed to fetch issue: {e}")
            raise HTTPException(status_code=404, detail=f"Issue not found: {e}")

        # Prepare query
        if request.query:
            user_query = request.query
        else:
            user_query = (
                f"Issue Title: {issue_title}\n\nIssue Description:\n{issue_body}"
            )

        logger.info(f"Running analysis with query length: {len(user_query)}")

        # Run analysis through agent
        analysis_result = _agent.run(user_query)

        # AUTO-GENERATE PATCH from analysis result
        patch_info = _generate_patch_internal(
            owner=request.owner,
            repo=request.repo,
            issue_id=request.issue_id,
            issue_title=issue_title,
            issue_body=issue_body,
            analysis=analysis_result,
        )

        return AnalysisResponse(
            issue_url=issue_url,
            issue_title=issue_title,
            issue_body=issue_body[:500],  # Truncate for response
            analysis=analysis_result,
            status="success",
            patch=patch_info,  # Include patch in response
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing issue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Send a custom query to the root agent.
    Attempts to generate a patch if the query results in actionable code changes.

    Args:
        query: The question to ask
    """
    try:
        if _agent is None:
            raise HTTPException(status_code=503, detail="Agent not initialized.")

        logger.info(f"Received query: {request.query[:100]}...")

        result = _agent.run(request.query)

        # TRY TO AUTO-GENERATE PATCH from query result
        # Only works if query is about a specific issue or code change
        patch_info = PatchInfo(status="not_generated")
        
        if _patch_agent and _current_repo_owner and _current_repo_name:
            try:
                # Check if the query mentions an issue ID
                import re
                issue_match = re.search(r'#(\d+)', request.query)
                if issue_match:
                    issue_id = int(issue_match.group(1))
                    logger.info(f"Detected issue #{issue_id} in query, attempting patch generation...")
                    
                    patch_result = _patch_agent.generate_patch(
                        issue_id=issue_id,
                        issue_title="Query Result Fix",
                        issue_body=request.query[:500],
                        analysis=result,
                    )
                    
                    if patch_result["status"] == "success":
                        patch_content = None
                        patch_file = patch_result.get("patch_file")
                        if patch_file and os.path.exists(patch_file):
                            try:
                                with open(patch_file, "r", encoding="utf-8") as f:
                                    patch_content = f.read()
                            except Exception as e:
                                logger.warning(f"Could not read patch file: {e}")
                        
                        patch_info = PatchInfo(
                            patch_file=patch_file,
                            patch_content=patch_content,
                            metadata_file=patch_result.get("metadata_file"),
                            commit_message=patch_result.get("commit_message"),
                            files_changed=patch_result.get("files_changed", []),
                            status="success",
                        )
            except Exception as e:
                logger.debug(f"Could not auto-generate patch from query: {e}")

        return QueryResponse(result=result, status="success", patch=patch_info)

    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "agent_initialized": _agent is not None,
        "vectorstore_initialized": _vectorstore is not None,
        "patch_agent_initialized": _patch_agent is not None,
        "current_repo": f"{_current_repo_owner}/{_current_repo_name}" if _current_repo_owner and _current_repo_name else None,
    }


@app.post("/api/build-rag", response_model=RAGBuildResponse)
async def build_rag_for_repo(request: RAGBuildRequest):
    """
    Build RAG knowledge base for a repository.
    
    This endpoint:
    1. Fetches repository content from GitHub
    2. Rebuilds the chroma_db in-place (no deletion needed)
    3. Reinitializes the agent with new data
    
    No server restart required - the vectorstore is automatically updated.

    Args:
        owner: Repository owner
        repo: Repository name
        save_code: Whether to save repository code to disk
    """
    try:
        global _vectorstore, _agent, _patch_agent, _current_repo_owner, _current_repo_name
        
        logger.info(f"Building RAG for {request.owner}/{request.repo}...")

        # Load repository content from GitHub
        logger.info("Fetching repository content from GitHub...")
        documents = get_repo_content_by_git(request.owner, request.repo)

        if not documents:
            raise HTTPException(
                status_code=400, detail="No documents retrieved from repository"
            )

        logger.info(f"Retrieved {len(documents)} documents")

        # Build RAG knowledge base
        # This will rebuild chroma_db in-place without any deletion
        logger.info("Building new RAG knowledge base...")
        vectorstore, saved_repo_path = create_rag_knowledge_base(
            documents,
            repo_owner=request.owner,
            repo_name=request.repo,
            save_repo_code=request.save_code,
            old_vectorstore=_vectorstore,  # Keep reference but don't close it
        )

        # Update global variables with new vectorstore
        _vectorstore = vectorstore
        _current_repo_owner = request.owner
        _current_repo_name = request.repo
        
        # Reinitialize agent with new vectorstore
        logger.info("Reinitializing agent with new vectorstore...")
        _agent = root_agent(_vectorstore)
        _initialize_patch_agent()

        logger.info("✓ RAG knowledge base rebuilt successfully")

        message = f"RAG knowledge base built for {request.owner}/{request.repo}"
        if saved_repo_path:
            message += f"\nRepository code saved to: {saved_repo_path}"

        return RAGBuildResponse(
            status="success",
            message=message,
            document_count=len(documents),
            saved_repo_path=saved_repo_path,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error building RAG: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"RAG build failed: {str(e)}")


@app.post("/api/generate-patch", response_model=PatchGenerationResponse)
async def generate_patch(request: PatchGenerationRequest):
    """
    Generate a git patch from an issue analysis

    Args:
        owner: Repository owner
        repo: Repository name
        issue_id: GitHub issue ID
        issue_title: GitHub issue title
        issue_body: GitHub issue description
        analysis: AI analysis of the issue
        query: Optional custom query for patch generation
    """
    try:
        if _patch_agent is None:
            raise HTTPException(
                status_code=503,
                detail="Patch agent not initialized. Please build RAG for the repository first.",
            )

        logger.info(f"Generating patch for issue #{request.issue_id}")

        # Generate patch
        result = _patch_agent.generate_patch(
            issue_id=request.issue_id,
            issue_title=request.issue_title,
            issue_body=request.issue_body,
            analysis=request.analysis,
            custom_query=request.query,
        )

        if result["status"] == "success":
            return PatchGenerationResponse(
                status="success",
                issue_id=result["issue_id"],
                issue_title=result["issue_title"],
                patch_file=result.get("patch_file"),
                metadata_file=result.get("metadata_file"),
                commit_message=result.get("commit_message"),
                files_changed=result.get("files_changed", []),
                specification=result.get("specification", ""),
            )
        elif result["status"] == "warning":
            return PatchGenerationResponse(
                status="warning",
                issue_id=request.issue_id,
                issue_title=request.issue_title,
                message=result.get("message"),
                specification=result.get("specification", ""),
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=result.get("message", "Failed to generate patch"),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating patch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Patch generation failed: {str(e)}")


@app.get("/api/patches", response_model=PatchListResponse)
async def list_patches():
    """
    List all generated patches

    Returns:
        List of patch information
    """
    try:
        if _patch_agent is None:
            return PatchListResponse(status="success", patches=[], total_count=0)

        patches = _patch_agent.list_generated_patches()

        return PatchListResponse(
            status="success", patches=patches, total_count=len(patches)
        )

    except Exception as e:
        logger.error(f"Error listing patches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list patches: {str(e)}")


@app.get("/api/patches/{patch_name}")
async def get_patch_details(patch_name: str):
    """
    Get detailed information about a specific patch

    Args:
        patch_name: Name of the patch file

    Returns:
        Patch details including metadata
    """
    try:
        if _patch_agent is None:
            raise HTTPException(status_code=503, detail="Patch agent not initialized")

        patch_details = _patch_agent.get_patch_details(patch_name)

        if patch_details is None:
            raise HTTPException(status_code=404, detail=f"Patch not found: {patch_name}")

        return patch_details

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting patch details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get patch details: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
