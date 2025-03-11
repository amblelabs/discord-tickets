from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import github_issues as issues
import os 
import discord
from dotenv import load_dotenv

load_dotenv()

URI = os.getenv("DATABASE_URL")
CLIENT = MongoClient(URI, server_api=ServerApi('1'))
DATABASE = CLIENT.get_database(os.getenv("DATABASE_NAME"))
COLLECTION = DATABASE.get_collection("tracking")

def track_issue(owner: str, repo: str, issue_number: int, thread_id: int) -> None:
    '''
        Track an issue in the database
    '''

    COLLECTION.insert_one({
        "owner": owner,
        "repo": repo,
        "issue_number": issue_number,
        "thread_id": thread_id
    })

def get_thread_id(owner: str, repo: str, issue_number: int) -> int:
    '''
        Get the thread id of an issue
    '''

    result = COLLECTION.find_one({
        "owner": owner,
        "repo": repo,
        "issue_number": issue_number
    })

    return result.get("thread_id", -1) if result else -1

def get_issue(thread_id: int) -> dict:
    '''
        Get the issue data from the database
    '''

    return COLLECTION.find_one({
        "thread_id": thread_id
    })

def get_tracked_issues(owner: str, repo: str) -> list:
    '''
        Get all the tracked issues in the database
    '''

    return list(COLLECTION.find({
        "owner": owner,
        "repo": repo
    }))


def untrack_issue(owner: str, repo: str, issue_number: int) -> None:
    '''
        Untrack an issue in the database
    '''

    COLLECTION.delete_one({
        "owner": owner,
        "repo": repo,
        "issue_number": issue_number
    })

def untrack_thread(thread_id: int) -> None:
    '''
        Untrack an issue in the database
    '''

    COLLECTION.delete_one({
        "thread_id": thread_id
    })

async def validate(data: dict) -> bool:
    '''
        Validate the data from the database
    '''

    # Check if issue is still open
    issue_data = issues.get_issue(data.get("owner"), data.get("repo"), data.get("issue_number"))
    if (issue_data.get("state") == "closed"):
        untrack_issue(data.get("owner"), data.get("repo"), data.get("issue_number"))
        return False

    return True

async def validate_all(owner: str, repo: str) -> None:
    '''
        Validate all the tracked issues
    '''

    for issue in get_tracked_issues(owner, repo):
        if (await validate(issue) == False):
            print(f"Untracked issue {issue.get('issue_number')}")