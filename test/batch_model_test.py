import asyncio
import logging
import os
import sys
import json
import time
from datetime import datetime
from typing import List, Dict
from statistics import mean, stdev

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

from agent.root_agent import root_agent
from tool.github_tool import get_issue_by_issue_id, get_repo_content_by_git
from tool.rag_tool import create_rag_knowledge_base

# Configuration
load_dotenv()
OLLAMA_EMBEDDING_MODEL = "embeddinggemma"
OLLAMA_BASE_URL = "http://localhost:11434"
CHROMA_DB_PATH = "./chroma_db"

# Batch test configuration
BATCH_SIZE = 100
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
    "kwaipilot/kat-coder-pro:free",
    "qwen/qwen3-coder:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-3-27b-it:free",
    "alibaba/tongyi-deepresearch-30b-a3b:free",
    "openai/gpt-oss-20b:free",
    "z-ai/glm-4.5-air:free",
    "meta-llama/llama-3.3-70b-instruct:free",
]


class BatchModelTester:
    """Batch test root_agent with different OpenRouter models"""

    def __init__(self, batch_size: int = 100):
        self.vectorstore = None
        self.batch_size = batch_size
        self.batch_results: Dict[str, Dict] = {}
        self.test_repo_owner = "psf"
        self.test_repo_name = "requests"
        self.test_issue_id = 6643
        
        # Setup output files with timestamp
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.test_name = f"batch_model_test_{self.batch_size}x_{self.timestamp}"
        self.results_json_path = os.path.join(OUTPUT_DIR, f"{self.test_name}_results.json")
        self.results_txt_path = os.path.join(OUTPUT_DIR, f"{self.test_name}_report.txt")
        self.summary_path = os.path.join(OUTPUT_DIR, f"{self.test_name}_summary.txt")

    async def setup_vectorstore(self):
        """Initialize vectorstore with psf/requests repository"""
        logger.info(f"Setting up vectorstore for {self.test_repo_owner}/{self.test_repo_name}...")

        try:
            if not os.path.exists(CHROMA_DB_PATH):
                logger.info("Building RAG knowledge base for test repository...")
                documents = get_repo_content_by_git(self.test_repo_owner, self.test_repo_name)

                if not documents:
                    logger.error("No documents retrieved from repository")
                    return False

                logger.info(f"Retrieved {len(documents)} documents")
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

    def fetch_test_issue(self) -> str:
        """Fetch a test issue from the repository"""
        logger.info(f"Fetching issue {self.test_issue_id} from {self.test_repo_owner}/{self.test_repo_name}...")

        try:
            issue = get_issue_by_issue_id(
                f"{self.test_repo_owner}/{self.test_repo_name}", self.test_issue_id
            )
            issue_title = issue.title
            issue_body = issue.body or "No description provided"
            user_query = f"Issue Title: {issue_title}\n\nIssue Description:\n{issue_body}"
            logger.info(f"Issue fetched: {issue_title}")
            return user_query, issue_title, issue_body

        except Exception as e:
            logger.error(f"Failed to fetch issue: {e}")
            logger.info("Using generic test query instead")
            return "What are the main features and purpose of the requests library?", None, None

    async def test_model_batch(self, model_name: str, user_query: str) -> Dict:
        """Test a model multiple times and record statistics"""
        logger.info(f"\nStarting batch tests for: {model_name} ({self.batch_size} iterations)")
        
        success_count = 0
        failure_count = 0
        output_lengths = []
        execution_times = []
        errors = []
        
        batch_start_time = time.time()
        
        for i in range(self.batch_size):
            try:
                agent = root_agent(self.vectorstore, model_name=model_name)
                
                test_start_time = time.time()
                result = agent.run(user_query)
                test_end_time = time.time()
                
                execution_time = test_end_time - test_start_time
                
                success_count += 1
                output_lengths.append(len(result))
                execution_times.append(execution_time)
                
                # Progress indicator every 10 tests
                if (i + 1) % 10 == 0:
                    logger.info(f"  {model_name}: {i + 1}/{self.batch_size} completed")
                
            except Exception as e:
                failure_count += 1
                errors.append(str(e))
        
        batch_end_time = time.time()
        total_batch_time = batch_end_time - batch_start_time
        
        # Calculate statistics
        stats = {
            "model": model_name,
            "total_tests": self.batch_size,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": (success_count / self.batch_size) * 100,
        }
        
        # Output length statistics
        if output_lengths:
            stats["avg_output_length"] = mean(output_lengths)
            stats["min_output_length"] = min(output_lengths)
            stats["max_output_length"] = max(output_lengths)
            if len(output_lengths) > 1:
                stats["std_dev_output_length"] = stdev(output_lengths)
            else:
                stats["std_dev_output_length"] = 0
        else:
            stats["avg_output_length"] = 0
            stats["min_output_length"] = 0
            stats["max_output_length"] = 0
            stats["std_dev_output_length"] = 0
        
        # Execution time statistics
        if execution_times:
            stats["total_execution_time"] = total_batch_time
            stats["avg_execution_time"] = mean(execution_times)
            stats["min_execution_time"] = min(execution_times)
            stats["max_execution_time"] = max(execution_times)
            if len(execution_times) > 1:
                stats["std_dev_execution_time"] = stdev(execution_times)
            else:
                stats["std_dev_execution_time"] = 0
        else:
            stats["total_execution_time"] = total_batch_time
            stats["avg_execution_time"] = 0
            stats["min_execution_time"] = 0
            stats["max_execution_time"] = 0
            stats["std_dev_execution_time"] = 0
        
        if errors:
            stats["sample_errors"] = errors[:5]  # Keep first 5 errors as samples
        
        logger.info(f"✓ Batch tests complete for {model_name}: {success_count}/{self.batch_size} success")
        logger.info(f"  Total time: {total_batch_time:.2f}s, Avg per test: {stats['avg_execution_time']:.2f}s")
        return stats

    async def run_batch_tests(self):
        """Run batch tests for all models"""
        logger.info(f"Starting batch model tests ({self.batch_size} iterations per model)...")
        
        # Setup vectorstore
        if not await self.setup_vectorstore():
            logger.error("Failed to setup vectorstore. Exiting tests.")
            return False

        # Fetch test issue
        user_query, issue_title, issue_body = self.fetch_test_issue()

        logger.info(f"Test query length: {len(user_query)}")
        logger.info(f"Testing {len(TEST_MODELS)} models with {self.batch_size} iterations each...")

        # Test each model
        for model_name in TEST_MODELS:
            stats = await self.test_model_batch(model_name, user_query)
            self.batch_results[model_name] = stats

        # Print and save results
        self._print_results(issue_title, issue_body)
        self._save_results(issue_title, issue_body, user_query)
        
        return True

    def _print_results(self, issue_title: str, issue_body: str):
        """Print batch test results summary"""
        logger.info("\n" + "="*80)
        logger.info("BATCH TEST RESULTS SUMMARY")
        logger.info("="*80)

        if issue_title:
            logger.info(f"\nTest Issue: {issue_title}")
            if issue_body:
                logger.info(f"Description (truncated): {issue_body[:200]}...")
        else:
            logger.info("\nGeneric test query used")

        logger.info(f"\nBatch Size: {self.batch_size} iterations per model")
        logger.info(f"Models Tested: {len(self.batch_results)}\n")

        for i, (model_name, stats) in enumerate(self.batch_results.items(), 1):
            logger.info(f"{'-'*80}")
            logger.info(f"Model {i}: {model_name}")
            logger.info(f"{'-'*80}")
            logger.info(f"Success: {stats['success_count']}/{stats['total_tests']} ({stats['success_rate']:.1f}%)")
            logger.info(f"Failures: {stats['failure_count']}/{stats['total_tests']}")
            logger.info(f"Avg Output Length: {stats['avg_output_length']:.0f} chars")
            logger.info(f"Min Output Length: {stats['min_output_length']} chars")
            logger.info(f"Max Output Length: {stats['max_output_length']} chars")
            if stats['std_dev_output_length'] > 0:
                logger.info(f"Std Dev: {stats['std_dev_output_length']:.0f} chars")
            logger.info(f"Total Execution Time: {stats['total_execution_time']:.2f}s")
            logger.info(f"Avg Execution Time: {stats['avg_execution_time']:.2f}s")
            logger.info(f"Min Execution Time: {stats['min_execution_time']:.2f}s")
            logger.info(f"Max Execution Time: {stats['max_execution_time']:.2f}s")
            if stats['std_dev_execution_time'] > 0:
                logger.info(f"Std Dev Execution Time: {stats['std_dev_execution_time']:.2f}s")

        # Comparison table
        logger.info(f"\n{'='*80}")
        logger.info("PERFORMANCE COMPARISON")
        logger.info(f"{'='*80}\n")
        
        # Sort by success rate
        sorted_stats = sorted(self.batch_results.items(), 
                            key=lambda x: x[1]['success_rate'], reverse=True)
        
        logger.info(f"{'Model':<50} {'Success Rate':<15} {'Avg Output':<15} {'Avg Time':<15}")
        logger.info("-" * 80)
        
        for model_name, stats in sorted_stats:
            logger.info(f"{model_name:<50} {stats['success_rate']:<14.1f}% {stats['avg_output_length']:<14.0f} {stats['avg_execution_time']:<14.2f}s")
        
        logger.info(f"\n{'='*80}\n")

    def _save_results(self, issue_title: str, issue_body: str, user_query: str):
        """Save batch test results to files"""
        logger.info(f"\nSaving batch test results to {OUTPUT_DIR}...")
        
        try:
            # Prepare data for JSON export
            json_data = {
                "timestamp": self.timestamp,
                "test_name": self.test_name,
                "batch_size": self.batch_size,
                "repository": f"{self.test_repo_owner}/{self.test_repo_name}",
                "issue_id": self.test_issue_id if issue_title else None,
                "issue_title": issue_title,
                "query_length": len(user_query),
                "models_tested": len(self.batch_results),
                "results": self.batch_results
            }
            
            # Save JSON results
            with open(self.results_json_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            logger.info(f"✓ JSON results saved to {self.results_json_path}")
            
            # Save detailed text report
            self._save_detailed_report(issue_title, issue_body, user_query)
            
            # Save summary comparison
            self._save_summary_report()
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

    def _save_detailed_report(self, issue_title: str, issue_body: str, user_query: str):
        """Save detailed text report"""
        with open(self.results_txt_path, "w", encoding="utf-8") as f:
            f.write("="*80 + "\n")
            f.write("BATCH MODEL TEST DETAILED REPORT\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Test Name: {self.test_name}\n")
            f.write(f"Timestamp: {self.timestamp}\n")
            f.write(f"Batch Size: {self.batch_size} iterations per model\n")
            f.write(f"Repository: {self.test_repo_owner}/{self.test_repo_name}\n\n")
            
            if issue_title:
                f.write(f"Test Issue: {issue_title}\n\n")
                if issue_body:
                    f.write("Issue Description:\n")
                    f.write("-"*80 + "\n")
                    f.write(issue_body + "\n")
            else:
                f.write("Generic test query used\n")
            
            f.write("\n" + "="*80 + "\n")
            f.write("QUERY USED FOR TESTING\n")
            f.write("="*80 + "\n\n")
            f.write(user_query + "\n\n")
            
            # Write detailed results for each model
            for i, (model_name, stats) in enumerate(self.batch_results.items(), 1):
                f.write("\n" + "="*80 + "\n")
                f.write(f"MODEL {i}: {model_name}\n")
                f.write("="*80 + "\n\n")
                
                f.write(f"Total Tests: {stats['total_tests']}\n")
                f.write(f"Successful Tests: {stats['success_count']}\n")
                f.write(f"Failed Tests: {stats['failure_count']}\n")
                f.write(f"Success Rate: {stats['success_rate']:.2f}%\n\n")
                
                f.write("Output Length Statistics:\n")
                f.write(f"  Average: {stats['avg_output_length']:.0f} characters\n")
                f.write(f"  Minimum: {stats['min_output_length']} characters\n")
                f.write(f"  Maximum: {stats['max_output_length']} characters\n")
                if stats['std_dev_output_length'] > 0:
                    f.write(f"  Std Dev: {stats['std_dev_output_length']:.0f} characters\n")
                
                f.write("Execution Time Statistics:\n")
                f.write(f"  Total: {stats['total_execution_time']:.2f} seconds\n")
                f.write(f"  Average: {stats['avg_execution_time']:.2f} seconds\n")
                f.write(f"  Minimum: {stats['min_execution_time']:.2f} seconds\n")
                f.write(f"  Maximum: {stats['max_execution_time']:.2f} seconds\n")
                if stats['std_dev_execution_time'] > 0:
                    f.write(f"  Std Dev: {stats['std_dev_execution_time']:.2f} seconds\n")
                
                if "sample_errors" in stats:
                    f.write(f"\nSample Errors (first 5):\n")
                    for j, error in enumerate(stats["sample_errors"], 1):
                        f.write(f"  {j}. {error[:100]}...\n")
            
            f.write("\n" + "="*80 + "\n")
        
        logger.info(f"✓ Detailed report saved to {self.results_txt_path}")

    def _save_summary_report(self):
        """Save summary comparison report"""
        with open(self.summary_path, "w", encoding="utf-8") as f:
            f.write("="*80 + "\n")
            f.write("BATCH TEST SUMMARY & COMPARISON\n")
            f.write("="*80 + "\n\n")
            
            f.write(f"Test Timestamp: {self.timestamp}\n")
            f.write(f"Batch Size: {self.batch_size} iterations per model\n")
            f.write(f"Total Models Tested: {len(self.batch_results)}\n\n")
            
            # Model status overview
            f.write("-"*80 + "\n")
            f.write("MODEL SUCCESS RATES\n")
            f.write("-"*80 + "\n\n")
            
            sorted_stats = sorted(self.batch_results.items(),
                                key=lambda x: x[1]['success_rate'], reverse=True)
            
            for rank, (model_name, stats) in enumerate(sorted_stats, 1):
                f.write(f"{rank}. {model_name}\n")
                f.write(f"   Success Rate: {stats['success_rate']:.2f}% ({stats['success_count']}/{stats['total_tests']})\n")
                f.write(f"   Avg Output Length: {stats['avg_output_length']:.0f} chars\n")
                f.write(f"   Avg Execution Time: {stats['avg_execution_time']:.2f} seconds\n\n")
            
            f.write("-"*80 + "\n")
            f.write("OUTPUT LENGTH COMPARISON\n")
            f.write("-"*80 + "\n\n")
            
            sorted_by_output = sorted(self.batch_results.items(),
                                    key=lambda x: x[1]['avg_output_length'], reverse=True)
            
            for rank, (model_name, stats) in enumerate(sorted_by_output, 1):
                f.write(f"{rank}. {model_name}\n")
                f.write(f"   Average: {stats['avg_output_length']:.0f} chars\n")
                f.write(f"   Min: {stats['min_output_length']} chars, Max: {stats['max_output_length']} chars\n\n")
            
            f.write("="*80 + "\n")
        
        logger.info(f"✓ Summary report saved to {self.summary_path}")
        logger.info(f"\nAll results saved to: {OUTPUT_DIR}/")


async def main():
    """Main batch test execution"""
    tester = BatchModelTester(batch_size=BATCH_SIZE)
    success = await tester.run_batch_tests()
    
    if success:
        logger.info("Batch tests completed successfully!")
    else:
        logger.error("Batch tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
