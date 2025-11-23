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
from backend.model import AnalysisRequest, AnalysisResponse, QueryRequest, QueryResponse
from tool.github_tool import get_issue_by_issue_id, get_repo_content_by_git

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


@app.on_event("startup")
async def startup_event():
    """Initialize agent on startup"""
    await initialize_agent()


# API Routes
@app.get("/")
async def read_root():
    """Serve the frontend HTML"""
    return FileResponse("server/frontend.html")


@app.post("/api/analyze-issue", response_model=AnalysisResponse)
async def analyze_issue(request: AnalysisRequest):
    """
    Analyze a GitHub issue using RAG and root agent

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

        return AnalysisResponse(
            issue_url=issue_url,
            issue_title=issue_title,
            issue_body=issue_body[:500],  # Truncate for response
            analysis=analysis_result,
            status="success",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing issue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.post("/api/query", response_model=QueryResponse)
async def query_agent(request: QueryRequest):
    """
    Send a custom query to the root agent

    Args:
        query: The question to ask
    """
    try:
        if _agent is None:
            raise HTTPException(status_code=503, detail="Agent not initialized.")

        logger.info(f"Received query: {request.query[:100]}...")

        result = _agent.run(request.query)

        return QueryResponse(result=result, status="success")

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
    }


@app.post("/api/build-rag")
async def build_rag_for_repo(request: AnalysisRequest):
    """
    Build RAG knowledge base for a repository

    Args:
        owner: Repository owner
        repo: Repository name
    """
    try:
        logger.info(f"Building RAG for {request.owner}/{request.repo}...")

        # Load repository content
        documents = get_repo_content_by_git(request.owner, request.repo)

        if not documents:
            raise HTTPException(
                status_code=400, detail="No documents retrieved from repository"
            )

        logger.info(f"Retrieved {len(documents)} documents")

        # Re-initialize vectorstore and agent with new documents
        from tool.rag_tool import create_rag_knowledge_base

        vectorstore = create_rag_knowledge_base(documents)

        global _vectorstore, _agent
        _vectorstore = vectorstore
        _agent = root_agent(_vectorstore)

        logger.info("RAG knowledge base rebuilt successfully")

        return {
            "status": "success",
            "message": f"RAG knowledge base built for {request.owner}/{request.repo}",
            "document_count": len(documents),
        }

    except Exception as e:
        logger.error(f"Error building RAG: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"RAG build failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
