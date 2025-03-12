import os # default module
import typing

import requests
from dotenv import load_dotenv

API_URL = "https://api.github.com"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OWNER = os.getenv("GITHUB_OWNER")
REPO = os.getenv("GITHUB_REPO")

HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

def get_issues(owner: str, repo: str, page: int = 1) -> list:
    """
    Get a list of issues from a GitHub repository.
    Returns ~30 issues per page.
    """

    params = {
        "page": page,
        "per_page": 30  # Adjust the number of issues per page as needed
    }

    url = f"repos/{owner}/{repo}/issues"
    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get issues: {response.status_code}")
        return []

def get_issue(owner: str, repo: str, issue_number: int) -> dict:
    """
    Get a single issue from a GitHub repository.
    """

    url = f"repos/{owner}/{repo}/issues/{issue_number}"
    response = requests.get(url, headers=HEADERS)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get issue: {response.status_code}")
        return {}

def get_issue_url(data: dict) -> str:
    """
    Get the URL of an issue from its JSON data.
    """

    return data.get("html_url", "")

def create_issue(owner: str, repo: str, title: str, body: str = "", assignees: list[str] = [], labels: list[str] = []) -> dict:
    """
    Create an issue in a GitHub repository.
    """

    url = f"repos/{owner}/{repo}/issues"

    data = {
        "title": title,
        "body": body,
        "assignees": assignees,
        "labels": labels
    }

    response = requests.post(url, headers=HEADERS, json=data)

    if response.status_code == 201:
        return response.json()
    else:
        print(f"Failed to create issue: {response.status_code}")
        return {}
    
def close_issue(owner: str, repo: str, issue_number: int) -> None:
    """
    Close an issue in a GitHub repository.
    """

    url = f"{API_URL}/repos/{owner}/{repo}/issues/{issue_number}"

    data = {
        "state": "closed"
    }

    response = requests.patch(url, headers=HEADERS, json=data)

    if response.status_code != 200:
        print(f"Failed to close issue: {response.status_code}")

def send_comment(owner: str, repo: str, issue_number: int, body: str) -> None:
    """
    Send a comment to an issue in a GitHub repository.
    """

    url = f"{API_URL}/repos/{owner}/{repo}/issues/{issue_number}/comments"

    data = {
        "body": body
    }

    response = requests.post(url, headers=HEADERS, json=data)

    if response.status_code != 201:
        print(f"Failed to send comment: {response.status_code}")