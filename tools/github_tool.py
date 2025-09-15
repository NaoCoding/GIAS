import os
from dotenv import load_dotenv

import github

load_dotenv()

def get_issue_by_issue_id(repo: str , id: int) -> github.Issue.Issue:

    g = github.Github(os.getenv("GITHUB_TOKEN"))
    result = g.get_repo(repo).get_issue(id)
    g.close()
    return result

