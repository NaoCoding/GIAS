import asyncio
import logging
import os
import sys
import json
from datetime import datetime
from typing import List, Dict

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from agent.root_agent import root_agent
from tool.github_tool import get_issue_by_issue_id, get_repo_content_by_git
from tool.rag_tool import create_rag_knowledge_base

# Configuration
load_dotenv()
OLLAMA_EMBEDDING_MODEL = "embeddinggemma"
OLLAMA_BASE_URL = "http://localhost:11434"
CHROMA_DB_PATH = "./chroma_db"

# Create output directory for test results
OUTPUT_DIR = "./test_results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Different OpenRouter models to test
TEST_MODELS = [
    "kwaipilot/kat-coder-pro:free",  # Default model
    "qwen/qwen3-coder:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-3-27b-it:free",
]


class TestRootAgentWithDifferentModels:
    """Test root_agent with different OpenRouter models on psf/requests repository"""

    def __init__(self):
        self.vectorstore = None
        self.test_results: Dict[str, Dict] = {}
        self.test_repo_owner = "psf"
        self.test_repo_name = "requests"
        self.test_issue_id = 6643  # Example issue ID - adjust if needed
        
        # Setup output files with timestamp
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_name = f"model_comparison_{self.timestamp}"
        self.results_json_path = os.path.join(OUTPUT_DIR, f"{self.test_name}_results.json")
        self.results_txt_path = os.path.join(OUTPUT_DIR, f"{self.test_name}_report.txt")
        self.summary_path = os.path.join(OUTPUT_DIR, f"{self.test_name}_summary.txt")

    async def setup_vectorstore(self):
        """Initialize vectorstore with psf/requests repository"""
        logger.info(f"Setting up vectorstore for {self.test_repo_owner}/{self.test_repo_name}...")

        try:
            # Check if chroma db already exists, if not build it
            if not os.path.exists(CHROMA_DB_PATH):
                logger.info("Building RAG knowledge base for test repository...")
                documents = get_repo_content_by_git(self.test_repo_owner, self.test_repo_name)

                if not documents:
                    logger.error("No documents retrieved from repository")
                    return False

                logger.info(f"Retrieved {len(documents)} documents")
                
                # Create vectorstore
                embeddings = OllamaEmbeddings(
                    model=OLLAMA_EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL
                )
                self.vectorstore = create_rag_knowledge_base(documents)
            else:
                logger.info(f"Loading existing vectorstore from {CHROMA_DB_PATH}...")
                embeddings = OllamaEmbeddings(
                    model=OLLAMA_EMBEDDING_MODEL, base_url=OLLAMA_BASE_URL
                )
                self.vectorstore = Chroma(
                    persist_directory=CHROMA_DB_PATH, embedding_function=embeddings
                )

            logger.info("Vectorstore initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to setup vectorstore: {e}")
            return False

    def fetch_test_issue(self) -> tuple:
        """Fetch a test issue from the repository"""
        logger.info(f"Fetching issue {self.test_issue_id} from {self.test_repo_owner}/{self.test_repo_name}...")

        try:
            issue = get_issue_by_issue_id(
                f"{self.test_repo_owner}/{self.test_repo_name}", self.test_issue_id
            )
            issue_title = issue.title
            issue_body = issue.body or "No description provided"
            issue_url = issue.html_url

            logger.info(f"Issue fetched: {issue_title}")
            return (issue_title, issue_body, issue_url)

        except Exception as e:
            logger.error(f"Failed to fetch issue: {e}")
            return (None, None, None)

    async def test_model(self, model_name: str, user_query: str) -> Dict:
        """Test root_agent with a specific model"""
        logger.info(f"\n{'='*80}")
        logger.info(f"Testing model: {model_name}")
        logger.info(f"{'='*80}")

        try:
            agent = root_agent(self.vectorstore, model_name=model_name)
            
            logger.info(f"Running analysis with {model_name}...")
            result = agent.run(user_query)
            
            logger.info(f"Analysis complete for {model_name}")
            
            return {
                "model": model_name,
                "status": "success",
                "result": result,
                "query_length": len(user_query),
            }

        except Exception as e:
            logger.error(f"Error testing model {model_name}: {e}")
            return {
                "model": model_name,
                "status": "error",
                "error": str(e),
            }

    async def run_tests(self):
        """Run all tests"""
        logger.info("Starting root_agent multi-model tests...")
        
        # Setup vectorstore
        if not await self.setup_vectorstore():
            logger.error("Failed to setup vectorstore. Exiting tests.")
            return False

        # Fetch test issue
        issue_title, issue_body, issue_url = self.fetch_test_issue()
        
        if not issue_title:
            logger.warning(
                f"Could not fetch issue {self.test_issue_id}. "
                "Using a generic test query instead."
            )
            user_query = "What are the main features and purpose of the requests library?"
        else:
            # Prepare query similar to frontend's analyze-issue endpoint
            user_query = f"Issue Title: {issue_title}\n\nIssue Description:\n{issue_body}"

        logger.info(f"Test query length: {len(user_query)}")

        # Test each model
        for model_name in TEST_MODELS:
            result = await self.test_model(model_name, user_query)
            self.test_results[model_name] = result

        # Print comprehensive results
        self._print_results(issue_title, issue_body, issue_url)
        
        # Save results to files
        self._save_results(issue_title, issue_body, issue_url, user_query)
        
        return True

    def _print_results(self, issue_title: str, issue_body: str, issue_url: str):
        """Print and compare test results"""
        logger.info("\n" + "="*80)
        logger.info("TEST RESULTS SUMMARY")
        logger.info("="*80)

        if issue_title:
            logger.info(f"\nTest Issue: {issue_title}")
            logger.info(f"URL: {issue_url}")
            logger.info(f"Description (truncated): {issue_body[:200]}...")
        else:
            logger.info("\nGeneric test query used")

        logger.info(f"\nTotal models tested: {len(self.test_results)}")

        for i, (model_name, result) in enumerate(self.test_results.items(), 1):
            logger.info(f"\n{'-'*80}")
            logger.info(f"Model {i}: {model_name}")
            logger.info(f"{'-'*80}")

            if result["status"] == "success":
                logger.info(f"Status: ✓ SUCCESS")
                logger.info(f"Result Preview (first 500 chars):")
                logger.info(f"\n{result['result'][:500]}...\n")
                logger.info(f"Full result length: {len(result['result'])} characters")
            else:
                logger.info(f"Status: ✗ ERROR")
                logger.info(f"Error: {result['error']}")

        # Detailed comparison
        logger.info(f"\n{'='*80}")
        logger.info("DETAILED COMPARISON")
        logger.info(f"{'='*80}\n")

        successful_results = {
            model: result for model, result in self.test_results.items()
            if result["status"] == "success"
        }

        if len(successful_results) >= 2:
            logger.info("Model outputs are available for comparison.")
            logger.info("Key observations:")
            
            result_lengths = {
                model: len(result["result"]) 
                for model, result in successful_results.items()
            }
            
            max_model = max(result_lengths, key=result_lengths.get)
            min_model = min(result_lengths, key=result_lengths.get)
            
            logger.info(f"  - Most verbose: {max_model} ({result_lengths[max_model]} chars)")
            logger.info(f"  - Most concise: {min_model} ({result_lengths[min_model]} chars)")
            logger.info(f"  - Difference: {result_lengths[max_model] - result_lengths[min_model]} chars")
        else:
            logger.warning("Not enough successful results for comparison")

        logger.info(f"\n{'='*80}\n")

    def _save_results(self, issue_title: str, issue_body: str, issue_url: str, user_query: str):
        """Save test results to files"""
        logger.info(f"\nSaving results to {OUTPUT_DIR}...")
        
        try:
            # Prepare data for JSON export
            json_data = {
                "timestamp": self.timestamp,
                "test_name": self.test_name,
                "repository": f"{self.test_repo_owner}/{self.test_repo_name}",
                "issue_id": self.test_issue_id if issue_title else None,
                "issue_title": issue_title,
                "issue_url": issue_url,
                "query_length": len(user_query),
                "models_tested": len(self.test_results),
                "results": {}
            }
            
            # Add individual model results
            for model_name, result in self.test_results.items():
                json_data["results"][model_name] = {
                    "status": result["status"],
                    "result_length": len(result.get("result", "")),
                    "error": result.get("error", None),
                    "full_result": result.get("result", "")
                }
            
            # Save JSON results
            with open(self.results_json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ JSON results saved to {self.results_json_path}")
            
            # Save detailed text report
            self._save_detailed_report(issue_title, issue_body, issue_url, user_query)
            
            # Save summary comparison
            self._save_summary_report()
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

    def _save_detailed_report(self, issue_title: str, issue_body: str, issue_url: str, user_query: str):
        """Save detailed text report with all results"""
        with open(self.results_txt_path, "w", encoding="utf-8") as f:
            f.write("="*80 + "\n")
            f.write("ROOT AGENT MULTI-MODEL TEST REPORT\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Test Name: {self.test_name}\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Repository: {self.test_repo_owner}/{self.test_repo_name}\n\n")
            
            if issue_title:
                f.write(f"Test Issue: {issue_title}\n")
                f.write(f"Issue URL: {issue_url}\n")
                f.write(f"Issue ID: {self.test_issue_id}\n\n")
                f.write("Issue Description:\n")
                f.write("-"*80 + "\n")
                f.write(issue_body + "\n")
            else:
                f.write("Generic test query used\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write("QUERY USED FOR TESTING\n")
            f.write("="*80 + "\n\n")
            f.write(user_query + "\n\n")
            
            # Write results for each model
            for i, (model_name, result) in enumerate(self.test_results.items(), 1):
                f.write("\n" + "="*80 + "\n")
                f.write(f"MODEL {i}: {model_name}\n")
                f.write("="*80 + "\n\n")
                
                if result["status"] == "success":
                    f.write("Status: ✓ SUCCESS\n\n")
                    f.write(f"Result Length: {len(result['result'])} characters\n\n")
                    f.write("Full Result:\n")
                    f.write("-"*80 + "\n")
                    f.write(result['result'] + "\n")
                else:
                    f.write("Status: ✗ ERROR\n\n")
                    f.write(f"Error: {result['error']}\n")
            
            f.write("\n" + "="*80 + "\n")
        
        logger.info(f"✓ Detailed report saved to {self.results_txt_path}")

    def _save_summary_report(self):
        """Save summary comparison report"""
        successful_results = {
            model: result for model, result in self.test_results.items()
            if result["status"] == "success"
        }
        
        with open(self.summary_path, "w", encoding="utf-8") as f:
            f.write("="*80 + "\n")
            f.write("TEST SUMMARY & COMPARISON\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Test Timestamp: {self.timestamp}\n")
            f.write(f"Total Models Tested: {len(self.test_results)}\n")
            f.write(f"Successful Tests: {len(successful_results)}\n")
            f.write(f"Failed Tests: {len(self.test_results) - len(successful_results)}\n\n")
            
            # Model status overview
            f.write("-"*80 + "\n")
            f.write("MODEL STATUS OVERVIEW\n")
            f.write("-"*80 + "\n\n")
            
            for model_name, result in self.test_results.items():
                status = "✓ SUCCESS" if result["status"] == "success" else "✗ FAILED"
                f.write(f"{model_name}: {status}\n")
            
            f.write("\n")
            
            if len(successful_results) >= 2:
                f.write("-"*80 + "\n")
                f.write("RESULT LENGTH COMPARISON\n")
                f.write("-"*80 + "\n\n")
                
                result_lengths = {
                    model: len(result["result"]) 
                    for model, result in successful_results.items()
                }
                
                # Sort by length
                sorted_results = sorted(result_lengths.items(), key=lambda x: x[1], reverse=True)
                
                for rank, (model, length) in enumerate(sorted_results, 1):
                    f.write(f"{rank}. {model}: {length} characters\n")
                
                max_model = sorted_results[0][0]
                min_model = sorted_results[-1][0]
                max_length = sorted_results[0][1]
                min_length = sorted_results[-1][1]
                
                f.write(f"\nMost Verbose: {max_model} ({max_length} chars)\n")
                f.write(f"Most Concise: {min_model} ({min_length} chars)\n")
                f.write(f"Difference: {max_length - min_length} characters\n")
            
            f.write("\n" + "="*80 + "\n")
        
        logger.info(f"✓ Summary report saved to {self.summary_path}")
        logger.info(f"\nAll results saved to: {OUTPUT_DIR}/")


async def main():
    """Main test execution"""
    tester = TestRootAgentWithDifferentModels()
    success = await tester.run_tests()
    
    if success:
        logger.info("All tests completed successfully!")
    else:
        logger.error("Tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
