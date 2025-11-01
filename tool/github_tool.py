import logging
import os

import github
from dotenv import load_dotenv
from langchain_core.documents import Document

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def get_issue_by_issue_id(repo: str, id: int) -> github.Issue.Issue:

    g = github.Github(GITHUB_TOKEN)
    result = g.get_repo(repo).get_issue(id)
    g.close()
    return result


def get_repo(repo: str) -> github.Repository.Repository:

    g = github.Github(GITHUB_TOKEN)
    result = g.get_repo(repo)
    g.close()
    return result


def get_repo_content(owner: str, name: str) -> list[Document]:
    """
    Uses PyGithub to recursively fetch code file contents from the repository.
    """
    logger.info(f"Connecting to GitHub and loading repository: {owner}/{name}...")

    g = github.Github(GITHUB_TOKEN)
    logger.info("Connection established.")

    try:
        repo = g.get_user(owner).get_repo(name)
        logger.info(f"Repository '{owner}/{name}' loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to connect or repository not found: {e}")
        return []

    all_docs = []

    def get_dir_contents(path: str):
        """Recursively traverses the repository contents."""
        try:
            contents = repo.get_contents(path)
            logger.debug(f"Fetched contents of directory: {path or 'root'}")
        except Exception:
            return

        for content in contents:
            if content.type == "dir":
                # Skip large or irrelevant folders
                if content.path.startswith(
                    (".git", "venv", "node_modules", "docs", "examples", "tests")
                ):
                    logger.debug(f"Skipping directory: {content.path}")
                    continue
                get_dir_contents(content.path)

            elif content.type == "file":
                # Process code files and check size limit
                is_code_file = content.path.endswith(
                    (".py", ".js", ".ts", ".go", ".java", ".c", ".cpp", ".h")
                )

                if not is_code_file or content.size > 1024 * 1024:
                    logger.debug(
                        f"Skipping non-code or large file: {content.path} (Size: {content.size} bytes)"
                    )
                    continue

                try:
                    # Fetch file content via API call
                    file_content = content.decoded_content.decode("utf-8")

                    # Create LangChain Document
                    doc = Document(
                        page_content=file_content,
                        metadata={
                            "source": f"{owner}/{name}/{content.path}",
                            "file_type": content.path.split(".")[-1],
                        },
                    )
                    all_docs.append(doc)
                    logger.debug(f"Processed file: {content.path}")

                except Exception as e:
                    logger.warning(f"Could not process file {content.path}: {e}")

    # Start traversal from the root
    get_dir_contents("")

    logger.info(f"PyGithub loading complete. Total code files fetched: {len(all_docs)}")
    return all_docs
