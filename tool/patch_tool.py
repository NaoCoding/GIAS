"""
Patch generation tool for creating git-compatible patches from code changes.
This tool generates unified diffs that can be applied using 'git apply' or 'patch' command.
"""

import logging
import os
import subprocess
import tempfile
from typing import Optional, Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PatchGenerator:
    """Generate and manage git patches from code changes."""

    def __init__(self, repo_owner: str, repo_name: str, output_dir: str = "./patches"):
        """
        Initialize patch generator.
        
        Args:
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            output_dir: Directory to save patch files
        """
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.output_dir = output_dir
        self.repo_full_name = f"{repo_owner}/{repo_name}"
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"PatchGenerator initialized for {self.repo_full_name}")

    def create_unified_diff(
        self,
        original_content: str,
        modified_content: str,
        file_path: str,
        context_lines: int = 3,
    ) -> str:
        """
        Create a unified diff between original and modified content.
        
        Args:
            original_content: Original file content
            modified_content: Modified file content
            file_path: Path to the file (for diff header)
            context_lines: Number of context lines around changes
            
        Returns:
            Unified diff string
        """
        import difflib

        original_lines = original_content.splitlines(keepends=True)
        modified_lines = modified_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
            n=context_lines,
        )

        return "\n".join(diff)

    def create_patch_file(
        self,
        changes: Dict[str, Dict[str, str]],
        patch_name: Optional[str] = None,
        description: str = "",
        author: str = "GIAS Agent",
    ) -> str:
        """
        Create a complete patch file from multiple changes.
        
        Args:
            changes: Dict mapping file paths to {'original': content, 'modified': content}
            patch_name: Optional name for the patch file (auto-generated if not provided)
            description: Description of the patch
            author: Author name for the patch metadata
            
        Returns:
            Path to the generated patch file
        """
        if not changes:
            raise ValueError("No changes provided for patch generation")

        # Generate patch filename if not provided
        if patch_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            patch_name = f"{self.repo_name}_fix_{timestamp}.patch"

        patch_path = os.path.join(self.output_dir, patch_name)

        # Build patch content
        patch_content = self._build_patch_header(description, author)

        # Add diffs for each changed file
        for file_path, content in changes.items():
            original = content.get("original", "")
            modified = content.get("modified", "")

            if original == modified:
                logger.warning(f"Skipping {file_path}: no changes detected")
                continue

            diff = self.create_unified_diff(original, modified, file_path)
            patch_content += "\n" + diff

        # Write patch file
        with open(patch_path, "w", encoding="utf-8") as f:
            f.write(patch_content)

        logger.info(f"Patch file created: {patch_path}")
        return patch_path

    def _build_patch_header(self, description: str, author: str) -> str:
        """Build the header section of a patch file."""
        timestamp = datetime.now().isoformat()
        header = f"""From: {author} <gias@github.local>
Date: {timestamp}
Subject: Fix for {self.repo_full_name}
X-GIAS-Repository: {self.repo_full_name}

{description}

---
"""
        return header

    def apply_patch(self, patch_path: str, target_dir: str, check_only: bool = False) -> bool:
        """
        Apply a patch file to a target directory.
        
        Args:
            patch_path: Path to the patch file
            target_dir: Target directory to apply patch to
            check_only: If True, only check if patch can be applied without actually applying it
            
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(patch_path):
            logger.error(f"Patch file not found: {patch_path}")
            return False

        try:
            # Prepare git apply command
            cmd = ["git", "apply"]
            if check_only:
                cmd.append("--check")

            with open(patch_path, "r", encoding="utf-8") as f:
                patch_content = f.read()

            # Run git apply in the target directory
            process = subprocess.run(
                cmd,
                input=patch_content.encode("utf-8"),
                cwd=target_dir,
                capture_output=True,
                timeout=30,
            )

            if process.returncode != 0:
                error_msg = process.stderr.decode("utf-8")
                logger.error(f"Failed to apply patch: {error_msg}")
                return False

            mode = "checked" if check_only else "applied"
            logger.info(f"Patch {mode} successfully: {patch_path}")
            return True

        except subprocess.TimeoutExpired:
            logger.error("Patch application timed out")
            return False
        except Exception as e:
            logger.error(f"Error applying patch: {e}")
            return False

    def create_commit_message(
        self, issue_id: int, issue_title: str, description: str
    ) -> str:
        """
        Create a git commit message.
        
        Args:
            issue_id: GitHub issue ID
            issue_title: GitHub issue title
            description: Detailed description of changes
            
        Returns:
            Formatted commit message
        """
        commit_msg = f"""Fix #{issue_id}: {issue_title}

{description}

Fixes: https://github.com/{self.repo_full_name}/issues/{issue_id}

Generated by GIAS (GitHub Issue Analysis System)
"""
        return commit_msg

    def save_patch_metadata(
        self,
        patch_name: str,
        issue_id: int,
        issue_title: str,
        analysis: str,
        files_changed: List[str],
    ) -> str:
        """
        Save metadata about the patch for reference.
        
        Args:
            patch_name: Name of the patch file
            issue_id: GitHub issue ID
            issue_title: GitHub issue title
            analysis: The analysis that led to the patch
            files_changed: List of files changed in the patch
            
        Returns:
            Path to the metadata file
        """
        import json

        metadata = {
            "timestamp": datetime.now().isoformat(),
            "repository": self.repo_full_name,
            "issue_id": issue_id,
            "issue_title": issue_title,
            "patch_file": patch_name,
            "analysis": analysis,
            "files_changed": files_changed,
        }

        metadata_path = os.path.join(
            self.output_dir, patch_name.replace(".patch", "_metadata.json")
        )

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Patch metadata saved: {metadata_path}")
        return metadata_path

    def list_patches(self) -> List[Dict[str, str]]:
        """
        List all generated patches.
        
        Returns:
            List of patch information dictionaries
        """
        patches = []
        for filename in os.listdir(self.output_dir):
            if filename.endswith(".patch"):
                patch_path = os.path.join(self.output_dir, filename)
                metadata_path = patch_path.replace(".patch", "_metadata.json")

                patch_info = {
                    "name": filename,
                    "path": patch_path,
                    "size": os.path.getsize(patch_path),
                    "created": datetime.fromtimestamp(
                        os.path.getctime(patch_path)
                    ).isoformat(),
                }

                # Load metadata if available
                if os.path.exists(metadata_path):
                    import json

                    with open(metadata_path, "r", encoding="utf-8") as f:
                        patch_info["metadata"] = json.load(f)

                patches.append(patch_info)

        return sorted(patches, key=lambda x: x["created"], reverse=True)
