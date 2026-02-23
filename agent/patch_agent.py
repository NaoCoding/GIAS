import logging
import os
import json
from typing import Optional, Dict, List

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

from agent.prompt.patch_agent import system_prompt
from tool.patch_tool import PatchGenerator

load_dotenv()
LLM_MODEL = "kwaipilot/kat-coder-pro:free"
openrouter_key = os.environ.get("OPEN_ROUTER_API_KEY")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class PatchAgent:
    """Agent specialized in generating code patches from issue analysis."""

    def __init__(
        self,
        vectorstore,
        repo_owner: str,
        repo_name: str,
        model_name: str = LLM_MODEL,
        patches_dir: str = "./patches",
    ):
        """
        Initialize the patch agent.

        Args:
            vectorstore: LangChain vectorstore with repository code
            repo_owner: Repository owner (GitHub)
            repo_name: Repository name (GitHub)
            model_name: LLM model to use
            patches_dir: Directory to save generated patches
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.patches_dir = patches_dir
        
        self._llm = ChatOpenAI(
            model=model_name,
            openai_api_base="https://openrouter.ai/api/v1",
            temperature=0.1,
            api_key=openrouter_key,
        )
        self._retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
        self._prompt = ChatPromptTemplate.from_template(system_prompt)
        
        self._patch_gen_chain = (
            {"context": self._retriever, "question": RunnablePassthrough()}
            | self._prompt
            | self._llm
            | StrOutputParser()
        )
        
        self._patch_generator = PatchGenerator(
            repo_owner, repo_name, output_dir=patches_dir
        )
        
        logger.info(f"PatchAgent initialized for {repo_owner}/{repo_name}")

    def generate_patch(
        self,
        issue_id: int,
        issue_title: str,
        issue_body: str,
        analysis: str,
        custom_query: Optional[str] = None,
    ) -> Dict:
        """
        Generate a patch from an issue analysis.

        Args:
            issue_id: GitHub issue ID
            issue_title: Issue title
            issue_body: Issue description
            analysis: AI analysis of the issue
            custom_query: Optional custom query for the agent

        Returns:
            Dictionary containing patch generation results
        """
        logger.info(f"Generating patch for issue #{issue_id}: {issue_title}")

        # Prepare the query for the agent
        query = custom_query or f"""
Based on this GitHub issue and analysis, generate a detailed patch/fix:

**Issue #{issue_id}: {issue_title}**

**Description:**
{issue_body[:1000]}

**Analysis:**
{analysis[:2000]}

Please provide:
1. A detailed explanation of the fix
2. Specific file paths that need to be changed
3. The exact code changes for each file (showing before and after)
4. How to test the changes
5. Any potential side effects or considerations

Format your response as a structured patch specification that can be converted to a git patch.
"""

        try:
            # Get patch specification from agent
            patch_spec = self._patch_gen_chain.invoke({"context": self._retriever, "question": query})
            
            logger.info("Patch specification generated")
            
            # Parse the patch specification
            changes = self._parse_patch_specification(patch_spec)
            
            if not changes:
                logger.warning("No code changes found in patch specification")
                return {
                    "status": "warning",
                    "message": "Patch specification generated but contains no code changes",
                    "specification": patch_spec,
                }
            
            # Create the actual patch file
            patch_filename = f"issue_{issue_id}_{self.repo_name}_fix.patch"
            patch_path = self._patch_generator.create_patch_file(
                changes=changes,
                patch_name=patch_filename,
                description=f"Fix for {issue_title}\n\nIssue: #{issue_id}\n{issue_body[:500]}",
                author="GIAS Patch Agent",
            )
            
            # Save metadata
            changed_files = list(changes.keys())
            metadata_path = self._patch_generator.save_patch_metadata(
                patch_filename=patch_filename,
                issue_id=issue_id,
                issue_title=issue_title,
                analysis=analysis,
                files_changed=changed_files,
            )
            
            # Create commit message
            commit_message = self._patch_generator.create_commit_message(
                issue_id=issue_id,
                issue_title=issue_title,
                description=analysis[:1000],
            )
            
            logger.info(f"Patch generated successfully: {patch_path}")
            
            return {
                "status": "success",
                "issue_id": issue_id,
                "issue_title": issue_title,
                "patch_file": patch_path,
                "metadata_file": metadata_path,
                "commit_message": commit_message,
                "files_changed": changed_files,
                "specification": patch_spec,
            }

        except Exception as e:
            logger.error(f"Error generating patch: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "issue_id": issue_id,
            }

    def _parse_patch_specification(self, spec_text: str) -> Dict[str, Dict[str, str]]:
        """
        Parse patch specification text to extract code changes.

        The specification should contain code blocks marked with file paths.
        Format:
        ```file: path/to/file.py
        # original code
        ---
        # modified code
        ```

        Args:
            spec_text: The patch specification text from the agent

        Returns:
            Dictionary mapping file paths to {'original': content, 'modified': content}
        """
        import re

        changes = {}

        # Look for code blocks with file markers
        # Pattern: ```file: path/to/file.py or similar
        pattern = r"```(?:file|path)?:?\s*([^\n]+)\n(.*?)\n```"
        matches = re.finditer(pattern, spec_text, re.DOTALL)

        for match in matches:
            file_path = match.group(1).strip()
            content = match.group(2).strip()

            # Split by "---" or "=>" to separate original and modified
            if "---" in content:
                parts = content.split("---", 1)
                original = parts[0].strip()
                modified = parts[1].strip() if len(parts) > 1 else original
            elif "=>" in content:
                parts = content.split("=>", 1)
                original = parts[0].strip()
                modified = parts[1].strip() if len(parts) > 1 else original
            else:
                # Assume entire content is the modified version
                original = ""
                modified = content

            changes[file_path] = {"original": original, "modified": modified}

        logger.info(f"Parsed {len(changes)} file changes from specification")
        return changes

    def list_generated_patches(self) -> List[Dict]:
        """List all patches generated by this agent."""
        return self._patch_generator.list_patches()

    def get_patch_details(self, patch_name: str) -> Optional[Dict]:
        """Get detailed information about a specific patch."""
        patches = self.list_generated_patches()
        for patch in patches:
            if patch["name"] == patch_name:
                return patch
        return None
