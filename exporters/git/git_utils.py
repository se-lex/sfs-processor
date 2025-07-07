"""Git utilities for SFS document processing."""

import subprocess
from datetime import datetime


def ensure_git_branch_for_commits(git_branch):
    """
    Ensures that git commits are made in a different branch than the current one.
    Creates a new branch if needed and switches to it.
    Returns the original branch name and the commit branch name.
    
    Args:
        git_branch: The branch name to use. If it contains "(timestamp)", 
                   that will be replaced with current timestamp.
    """
    try:
        # Get current branch name
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], 
                              capture_output=True, text=True, check=True)
        current_branch = result.stdout.strip()

        # Generate commit branch name
        if "(timestamp)" in git_branch:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            commit_branch = git_branch.replace("(timestamp)", timestamp)
        else:
            commit_branch = git_branch

        # Create and switch to the new branch
        subprocess.run(['git', 'checkout', '-b', commit_branch], 
                      check=True, capture_output=True)

        print(f"Skapade och bytte till branch '{commit_branch}' för git-commits")
        return current_branch, commit_branch

    except subprocess.CalledProcessError as e:
        print(f"Varning: Kunde inte skapa ny branch för git-commits: {e}")
        return None, None
    except FileNotFoundError:
        print("Varning: Git hittades inte.")
        return None, None


def restore_original_branch(original_branch):
    """
    Switches back to the original branch after commits are done.
    """
    if not original_branch:
        return
        
    try:
        subprocess.run(['git', 'checkout', original_branch], 
                      check=True, capture_output=True)
        print(f"Bytte tillbaka till ursprunglig branch '{original_branch}'")
    except subprocess.CalledProcessError as e:
        print(f"Varning: Kunde inte byta tillbaka till ursprunglig branch: {e}")
    except FileNotFoundError:
        print("Varning: Git hittades inte.")
