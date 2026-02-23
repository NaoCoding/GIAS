# Quick Start Guide - New Features

## What's New in GIAS

Your system now has three major new capabilities:

1. ✅ **Patch Generation Agent** - Automatically generate git patches from analyses
2. ✅ **Code Repository Saving** - Save analyzed code to disk for easy testing
3. ✅ **Enhanced API** - New endpoints for patch management

---

## Quick Start: 5-Minute Setup

### 1. Create Required Directories

```bash
# From GIAS root directory
mkdir -p patches
mkdir -p saved_repos
```

### 2. Update Your Environment

The new features work with existing dependencies - no new package installations needed!

### 3. Start Using It

#### Option A: Via API (Recommended)

```bash
# Terminal 1: Start the backend
cd GIAS
python -m backend.server
# Server runs on http://localhost:8000
```

```bash
# Terminal 2: Test the new features

# 1. Build RAG and save repository code
curl -X POST http://localhost:8000/api/build-rag \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "psf",
    "repo": "requests",
    "save_code": true
  }'

# Check the response for saved_repo_path
# Example output: "./saved_repos/psf_requests_20260223_103000"

# 2. Analyze an issue
curl -X POST http://localhost:8000/api/analyze-issue \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "psf",
    "repo": "requests",
    "issue_id": 6643,
    "query": null
  }'

# 3. Generate a patch from the analysis
curl -X POST http://localhost:8000/api/generate-patch \
  -H "Content-Type: application/json" \
  -d '{
    "owner": "psf",
    "repo": "requests",
    "issue_id": 6643,
    "issue_title": "Leading slash in uri followed by column fails",
    "issue_body": "When making a request with //v:h pattern...",
    "analysis": "[Use analysis result from step 2]"
  }'

# 4. List all generated patches
curl http://localhost:8000/api/patches

# 5. Get details about a specific patch
curl http://localhost:8000/api/patches/issue_6643_requests_fix.patch
```

#### Option B: Via Python Code

```python
import asyncio
from agent.root_agent import root_agent
from agent.patch_agent import PatchAgent
from tool.rag_tool import create_rag_knowledge_base
from tool.github_tool import get_issue_by_issue_id, get_repo_content_by_git
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma

async def example_workflow():
    # 1. Build RAG with code saving
    print("📚 Building RAG knowledge base...")
    documents = get_repo_content_by_git("psf", "requests")
    vectorstore, saved_path = create_rag_knowledge_base(
        documents,
        repo_owner="psf",
        repo_name="requests",
        save_repo_code=True
    )
    print(f"✓ Code saved to: {saved_path}")
    
    # 2. Initialize agents
    print("\n🤖 Initializing agents...")
    analysis_agent = root_agent(vectorstore)
    patch_agent = PatchAgent(vectorstore, "psf", "requests")
    
    # 3. Analyze issue
    print("\n🔍 Analyzing issue...")
    issue = get_issue_by_issue_id("psf/requests", 6643)
    analysis = analysis_agent.run(f"Issue: {issue.title}\n\n{issue.body}")
    print(f"Analysis complete: {len(analysis)} characters")
    
    # 4. Generate patch
    print("\n🔧 Generating patch...")
    result = patch_agent.generate_patch(
        issue_id=6643,
        issue_title=issue.title,
        issue_body=issue.body,
        analysis=analysis
    )
    
    # 5. Display results
    if result["status"] == "success":
        print(f"\n✅ Success!")
        print(f"   Patch: {result['patch_file']}")
        print(f"   Files changed: {', '.join(result['files_changed'])}")
        print(f"\nCommit message:\n{result['commit_message']}")
    else:
        print(f"\n❌ Error: {result.get('message')}")

# Run it
asyncio.run(example_workflow())
```

---

## Feature Details

### 📋 Patch Generation

**What it does:**
- Analyzes AI recommendations
- Extracts code changes from the analysis
- Creates git-compatible unified diff patches
- Generates professional commit messages
- Saves metadata about the patch

**Output files:**
- `issue_XXXX_reponame_fix.patch` - The actual patch file
- `issue_XXXX_reponame_fix_metadata.json` - Metadata JSON

**Example patch file content:**
```
From: GIAS Patch Agent <gias@github.local>
Date: 2026-02-23T10:30:00
Subject: Fix for requests
X-GIAS-Repository: psf/requests

Fix for Leading slash in uri followed by column fails...

---
--- a/requests/utils.py
+++ b/requests/utils.py
@@ -100,7 +100,7 @@
    def normalize_url(url):
        # Original code
-       return url
+       return url.strip()
```

### 💾 Repository Code Saving

**What it does:**
- Saves all analyzed repository files to disk
- Preserves directory structure
- Creates timestamped snapshots
- Adds metadata file

**Directory structure:**
```
saved_repos/
└── psf_requests_20260223_103000/
    ├── .gias_metadata.json
    ├── requests/
    │   ├── __init__.py
    │   ├── utils.py
    │   └── models.py
    ├── tests/
    │   └── test_utils.py
    └── README.md
```

**Benefits:**
- Offline access to analyzed code
- Easy to diff against patches
- Archive for reference
- Testing and validation

### 🔧 Using Generated Patches

**Check if patch applies cleanly:**
```bash
cd /path/to/repository
git apply --check /path/to/patch/issue_6643_requests_fix.patch
```

**Apply the patch:**
```bash
git apply /path/to/patch/issue_6643_requests_fix.patch
```

**Or using patch command:**
```bash
patch -p1 < /path/to/patch/issue_6643_requests_fix.patch
```

**Create a commit:**
```bash
# Copy the commit message from the patch metadata
# or from the API response
git add .
git commit -m "Fix #6643: Leading slash in uri followed by column fails

The issue is caused by..."
```

---

## API Reference

### Endpoints Summary

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/build-rag` | Build RAG and optionally save code |
| POST | `/api/analyze-issue` | Analyze a GitHub issue |
| POST | `/api/generate-patch` | Generate patch from analysis |
| GET | `/api/patches` | List all generated patches |
| GET | `/api/patches/{name}` | Get patch details |
| POST | `/api/query` | Query the analysis agent |
| GET | `/api/health` | Health check |

### Response Status Codes

- `200` - Success
- `400` - Bad request
- `404` - Not found
- `500` - Server error
- `503` - Service unavailable (Ollama/vector store not ready)

---

## Troubleshooting

### "Patch agent not initialized"
**Solution:** Build RAG for a repository first
```bash
curl -X POST http://localhost:8000/api/build-rag \
  -H "Content-Type: application/json" \
  -d '{"owner":"psf","repo":"requests","save_code":true}'
```

### "No code changes found"
**Solution:** The analysis might not have code blocks. Check the analysis format:
- Analysis should include code sections marked with ` ``` `
- Format should show original and modified code separated by `---` or `=>`

### Patch file is empty
**Solution:** Verify the response has files_changed array
```bash
curl http://localhost:8000/api/patches/issue_XXXX_repo_fix.patch
# Check the metadata file for file list
```

### Saved repository path not returned
**Solution:** Ensure `save_code: true` in build-rag request

---

## Advanced Usage

### Custom Patch Generation Queries

```python
result = patch_agent.generate_patch(
    issue_id=6643,
    issue_title="Bug fix",
    issue_body="Description",
    analysis="AI analysis",
    custom_query="Please focus on performance optimizations in the patch"
)
```

### Listing Patches Programmatically

```python
patches = patch_agent.list_generated_patches()
for patch in patches:
    print(f"Patch: {patch['name']}")
    print(f"  Created: {patch['created']}")
    print(f"  Size: {patch['size']} bytes")
    if 'metadata' in patch:
        print(f"  Issue: #{patch['metadata']['issue_id']}")
        print(f"  Files: {len(patch['metadata']['files_changed'])}")
```

### Applying Patches Programmatically

```python
from tool.patch_tool import PatchGenerator

gen = PatchGenerator("psf", "requests")
success = gen.apply_patch(
    patch_path="./patches/issue_6643_requests_fix.patch",
    target_dir="/path/to/requests/repo",
    check_only=False  # True to only check if it applies
)

if success:
    print("✓ Patch applied successfully")
else:
    print("✗ Patch application failed")
```

---

## File Organization After Setup

```
GIAS/
├── agent/
│   ├── root_agent.py           ✓ (existing, unchanged)
│   ├── patch_agent.py          ✨ NEW
│   └── prompt/
│       ├── root_agent.py       ✓ (existing)
│       └── patch_agent.py      ✨ NEW
├── tool/
│   ├── github_tool.py          ✓ (existing)
│   ├── rag_tool.py             ✨ ENHANCED
│   └── patch_tool.py           ✨ NEW
├── backend/
│   ├── server.py               ✨ ENHANCED
│   └── model.py                ✨ ENHANCED
├── patches/                    📁 NEW (empty, auto-populated)
├── saved_repos/                📁 NEW (empty, auto-populated)
└── IMPROVEMENTS.md             📖 NEW (this documentation)
```

---

## Summary of Changes

### New Files Created
- `agent/patch_agent.py` - Patch generation agent
- `agent/prompt/patch_agent.py` - Patch agent prompt template
- `tool/patch_tool.py` - Patch generation utilities
- `IMPROVEMENTS.md` - Detailed documentation

### Files Enhanced
- `tool/rag_tool.py` - Added code saving functionality
- `backend/server.py` - Added 4 new API endpoints
- `backend/model.py` - Added 4 new request/response models

### New Directories Created
- `patches/` - Stores generated patch files
- `saved_repos/` - Stores snapshots of analyzed repositories

### Backward Compatibility
✅ All existing functionality remains unchanged
✅ Existing API endpoints work as before
✅ No breaking changes to existing code
✅ RAG building works with or without code saving

---

## Next Steps

1. ✅ Review the `IMPROVEMENTS.md` file for detailed documentation
2. ✅ Create the required directories
3. ✅ Test with a small repository first (like `psf/requests`)
4. ✅ Generate your first patch using the examples above
5. ✅ Validate the patches and integrate with your workflow

---

## Support Resources

- **Detailed Guide**: Read `IMPROVEMENTS.md`
- **API Documentation**: Check backend server logs
- **Patch Metadata**: Look in the patch metadata JSON files
- **Error Messages**: Check backend console output for detailed errors

Enjoy your enhanced GIAS system! 🚀
