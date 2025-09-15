import requests
import os
from dotenv import load_dotenv

from github import Github
from github import Auth

load_dotenv()

def get_issue_by_issue_id(repo: str , id: int):

    # github_auth = Auth.Token(os.getenv("GITHUB_TOKEN"))
    g = Github(os.getenv("GITHUB_TOKEN"))
    result = g.get_repo(repo).get_issue(id)
    g.close()
    return result

