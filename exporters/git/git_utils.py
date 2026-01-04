"""Git utilities for SFS document processing."""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Git main branch name
GIT_MAIN_BRANCH = "main"

# Git command timeout in seconds (10 minutes)
GIT_TIMEOUT = 600

# Default target repository
DEFAULT_TARGET_REPO = "https://github.com/se-lex/sfs.git"


def prepare_git_branch(git_branch, remove_all_commits_first=True, verbose=False):
    """
    Ensures that git commits are made in a different branch than the current one.
    Creates a new branch if needed and switches to it.
    Returns the original branch name and the commit branch name.

    Args:
        git_branch: The branch name to use. If it contains "(date)",
                   that will be replaced with current date.
        remove_all_commits_first: If True, removes all commits on the branch before proceeding.
        verbose: If True, print detailed information.
    """
    try:
        # Get current branch name
        result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                capture_output=True, text=True, check=True, timeout=GIT_TIMEOUT)
        current_branch = result.stdout.strip()

        # Generate commit branch name
        if "(date)" in git_branch:
            date_str = datetime.now().strftime("%Y%m%d")
            commit_branch = git_branch.replace("(date)", date_str)
        else:
            commit_branch = git_branch

        # Create and switch to the new branch
        subprocess.run(['git', 'checkout', '-b', commit_branch],
                       check=True, capture_output=True, timeout=GIT_TIMEOUT)

        print(f"Skapade och bytte till branch '{commit_branch}' för git-commits")

        # Remove all commits on branch if requested
        if remove_all_commits_first:
            removed_commits = remove_all_commits_on_branch(verbose=verbose)
            if removed_commits > 0:
                print(f"Tog bort {removed_commits} tidigare commits från branchen")

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
                       check=True, capture_output=True, timeout=GIT_TIMEOUT)
        print(f"Bytte tillbaka till ursprunglig branch '{original_branch}'")
    except subprocess.CalledProcessError as e:
        print(f"Varning: Kunde inte byta tillbaka till ursprunglig branch: {e}")
    except FileNotFoundError:
        print("Varning: Git hittades inte.")


def remove_all_commits_on_branch(branch_name=None, verbose=False):
    """
    Remove all commits on the specified branch (or current branch) that are not on the main branch.

    Args:
        branch_name: The branch to remove commits from. If None, uses current branch.
        verbose: If True, print detailed information about removed commits.

    Returns:
        int: Number of commits removed
    """
    try:
        # If branch_name is provided, switch to it first
        original_branch = None
        if branch_name:
            # Get current branch
            result = subprocess.run(['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                                    capture_output=True, text=True, check=True, timeout=GIT_TIMEOUT)
            original_branch = result.stdout.strip()

            # Switch to target branch if different
            if original_branch != branch_name:
                subprocess.run(['git', 'checkout', branch_name],
                               check=True, capture_output=True, timeout=GIT_TIMEOUT)

        # Get the merge base with main branch (the point where current branch diverged)
        result = subprocess.run([
            'git', 'merge-base', 'HEAD', GIT_MAIN_BRANCH
        ], capture_output=True, text=True, check=True, timeout=GIT_TIMEOUT)

        merge_base = result.stdout.strip()

        # Find all commits on current branch since merge base
        result = subprocess.run([
            'git', 'log',
            f'{merge_base}..HEAD',
            '--format=%H %s',
            '--reverse'  # Show oldest first
        ], capture_output=True, text=True, check=True, timeout=GIT_TIMEOUT)

        commits_to_remove = result.stdout.strip().split('\n') if result.stdout.strip() else []

        if not commits_to_remove:
            if verbose:
                print("Inga commits att ta bort på denna branch")
            return 0

        if verbose:
            print(f"Tar bort {len(commits_to_remove)} commits på branchen:")
            for commit_info in commits_to_remove:
                print(f"  - {commit_info}")

        # Reset to merge base (hard reset to remove all changes)
        subprocess.run(['git', 'reset', '--hard', merge_base],
                       check=True, capture_output=True, timeout=GIT_TIMEOUT)

        print(f"Tog bort {len(commits_to_remove)} commits från branchen")

        # Switch back to original branch if we switched
        if original_branch and original_branch != branch_name:
            subprocess.run(['git', 'checkout', original_branch],
                           check=True, capture_output=True, timeout=GIT_TIMEOUT)

        return len(commits_to_remove)

    except subprocess.CalledProcessError as e:
        print(f"Varning: Kunde inte ta bort commits: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            if isinstance(e.stderr, bytes):
                print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
            else:
                print(f"Git stderr: {e.stderr}")
        return 0
    except FileNotFoundError:
        print("Varning: Git hittades inte.")
        return 0


def get_target_repository() -> str:
    """
    Get the target repository URL from environment variable or use default.

    Returns:
        str: Repository URL to push to
    """
    return os.getenv('GIT_TARGET_REPO', DEFAULT_TARGET_REPO)


def configure_git_remote(repo_url: str, remote_name: str = 'target', verbose: bool = False) -> bool:
    """
    Configure a git remote for pushing commits.

    Args:
        repo_url: URL of the target repository
        remote_name: Name for the remote (default: 'target')
        verbose: Enable verbose output

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Check if remote already exists
        result = subprocess.run(['git', 'remote', 'get-url', remote_name],
                                capture_output=True, timeout=GIT_TIMEOUT)

        if result.returncode == 0:
            # Remote exists, update it
            subprocess.run(['git', 'remote', 'set-url', remote_name, repo_url],
                           check=True, capture_output=True, timeout=GIT_TIMEOUT)
            if verbose:
                print(f"Uppdaterade remote '{remote_name}' till {repo_url}")
        else:
            # Remote doesn't exist, add it
            subprocess.run(['git', 'remote', 'add', remote_name, repo_url],
                           check=True, capture_output=True, timeout=GIT_TIMEOUT)
            if verbose:
                print(f"Lade till remote '{remote_name}': {repo_url}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"Fel vid konfiguration av git remote: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
        return False


def create_authenticated_url(repo_url: str, pat_token: str) -> str:
    """
    Create an authenticated URL using PAT token.

    Args:
        repo_url: Original repository URL
        pat_token: Personal Access Token

    Returns:
        str: Authenticated URL
    """
    if not pat_token:
        return repo_url

    parsed = urlparse(repo_url)
    if parsed.hostname == 'github.com':
        # For GitHub, use token as username
        return f"https://{pat_token}@github.com{parsed.path}"
    else:
        # For other hosts, keep original URL
        return repo_url


def clone_target_repository_to_temp(verbose: bool = False) -> tuple[Path, str]:
    """
    Clone target repository to a temporary directory.

    Args:
        verbose: Enable verbose output

    Returns:
        tuple[Path, str]: (repo_directory_path, original_cwd) or (None, None) if failed
    """
    import tempfile

    try:
        # Get repository URL and PAT token
        repo_url = get_target_repository()
        pat_token = os.getenv('GIT_GITHUB_PAT')

        # Try to load PAT from .env file if not in environment
        if not pat_token:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                pat_token = os.getenv('GIT_GITHUB_PAT')
            except ImportError:
                pass  # dotenv not available

        # Create authenticated URL if PAT is available
        if pat_token:
            auth_url = create_authenticated_url(repo_url, pat_token)
        else:
            auth_url = repo_url
            if verbose:
                print("Varning: Ingen PAT token hittades, använder okrypterad URL")

        # Create temporary directory for cloning
        temp_dir = tempfile.mkdtemp()
        repo_dir = Path(temp_dir) / "target_repo"

        if verbose:
            print(f"Klonar {repo_url} till temporär katalog...")

        # Clone the repository
        subprocess.run([
            'git', 'clone', auth_url, str(repo_dir)
        ], check=True, capture_output=True, timeout=GIT_TIMEOUT)

        # Remember original directory
        original_cwd = os.getcwd()

        return repo_dir, original_cwd

    except subprocess.CalledProcessError as e:
        print(f"Fel vid kloning av target repository: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
        return None, None
    except Exception as e:
        print(f"Oväntat fel vid kloning av target repository: {e}")
        return None, None


def is_file_tracked(file_path: str) -> bool:
    """
    Check if a file is already tracked by git.

    Args:
        file_path: Path to the file to check

    Returns:
        bool: True if file is tracked, False otherwise
    """
    try:
        result = subprocess.run(['git', 'ls-files', file_path],
                                capture_output=True, text=True, timeout=GIT_TIMEOUT)
        return result.returncode == 0 and result.stdout.strip() != ""
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False


def has_staged_changes() -> bool:
    """
    Check if there are any staged changes ready to commit.

    Returns:
        bool: True if there are staged changes, False otherwise
    """
    try:
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'],
                                capture_output=True, timeout=GIT_TIMEOUT)
        # git diff --cached --quiet returns 0 if there are no changes, 1 if there are changes
        return result.returncode != 0
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False


def stage_file(file_path: str, verbose: bool = False) -> bool:
    """
    Stage a file for git commit.

    Args:
        file_path: Path to the file to stage
        verbose: Enable verbose output

    Returns:
        bool: True if staging was successful, False otherwise
    """
    try:
        subprocess.run(['git', 'add', file_path],
                       check=True, capture_output=True, timeout=GIT_TIMEOUT)

        if verbose:
            print(f"Stagade fil: {file_path}")

        return True

    except subprocess.CalledProcessError as e:
        print(f"Fel vid staging av {file_path}: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
        return False
    except FileNotFoundError:
        print("Varning: Git hittades inte.")
        return False


def checkout_branch(
        branch_name: str,
        create_if_missing: bool = True,
        verbose: bool = False) -> bool:
    """
    Checkout to a git branch, optionally creating it if it doesn't exist.

    Args:
        branch_name: Name of the branch to checkout
        create_if_missing: If True, create the branch if it doesn't exist
        verbose: Enable verbose output

    Returns:
        bool: True if checkout was successful, False otherwise
    """
    try:
        # Try to checkout the branch first
        result = subprocess.run(['git', 'checkout', branch_name],
                                capture_output=True, timeout=GIT_TIMEOUT)

        if result.returncode == 0:
            if verbose:
                print(f"Bytte till branch '{branch_name}'")
            return True
        elif create_if_missing:
            # Branch doesn't exist, create it
            subprocess.run(['git', 'checkout', '-b', branch_name],
                           check=True, capture_output=True, timeout=GIT_TIMEOUT)
            if verbose:
                print(f"Skapade och bytte till branch '{branch_name}'")
            return True
        else:
            if verbose:
                print(f"Branch '{branch_name}' finns inte och create_if_missing=False")
            return False

    except subprocess.CalledProcessError as e:
        print(f"Fel vid checkout av branch '{branch_name}': {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
        return False
    except FileNotFoundError:
        print("Varning: Git hittades inte.")
        return False


def check_duplicate_commit_message(message: str, verbose: bool = False) -> bool:
    """
    Check if a commit with the given message already exists in the current branch.

    Args:
        message: Commit message to check
        verbose: Enable verbose output

    Returns:
        bool: True if a duplicate exists, False otherwise
    """
    try:
        # Search for commits with the exact message
        result = subprocess.run([
            'git', 'log', '--grep', f'^{message}$', '--format=%H', '-n', '1'
        ], capture_output=True, text=True, timeout=GIT_TIMEOUT)

        has_duplicate = result.returncode == 0 and result.stdout.strip() != ""

        if has_duplicate and verbose:
            commit_hash = result.stdout.strip()
            print(f"Varning: En commit med samma meddelande finns redan: {commit_hash}")

        return has_duplicate

    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"Fel vid sökning efter duplicerad commit: {e}")
        return False
    except FileNotFoundError:
        if verbose:
            print("Varning: Git hittades inte.")
        return False


def create_commit_with_date(message: str, date: str, verbose: bool = False) -> bool:
    """
    Create a git commit with a specified date.

    Args:
        message: Commit message
        date: Date string in format that git accepts (e.g., "2024-01-01 12:00:00 +0100")
        verbose: Enable verbose output

    Returns:
        bool: True if commit was successful, False otherwise
    """
    try:
        # Check for duplicate commit message
        if check_duplicate_commit_message(message, verbose):
            raise ValueError(f"En commit med meddelandet '{message}' finns redan!")

        # Set both author and committer dates
        env = {**os.environ, 'GIT_AUTHOR_DATE': date, 'GIT_COMMITTER_DATE': date}

        subprocess.run([
            'git', 'commit', '-m', message
        ], check=True, capture_output=True, env=env, timeout=GIT_TIMEOUT)

        if verbose:
            print(f"Git-commit skapad: '{message}' daterad {date}")

        return True

    except ValueError as e:
        print(f"❌ Fel: {e}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Fel vid commit: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
        return False
    except FileNotFoundError:
        print("Varning: Git hittades inte.")
        return False


def push_to_target_repository(
        branch_name: str,
        remote_name: str = 'target',
        verbose: bool = False) -> bool:
    """
    Push the specified branch to the target repository.

    Args:
        branch_name: Name of the branch to push
        remote_name: Name of the remote to push to
        verbose: Enable verbose output

    Returns:
        bool: True if push was successful, False otherwise
    """
    try:
        # Protect against pushing to main branch
        if branch_name == GIT_MAIN_BRANCH:
            print(f"❌ Fel: Kan inte pusha till main branch '{GIT_MAIN_BRANCH}' för säkerhet")
            print(f"Använd ensure_git_branch_for_commits() för att skapa en separat branch först")
            return False

        # Get repository URL and PAT token
        repo_url = get_target_repository()
        pat_token = os.getenv('GIT_GITHUB_PAT')

        # Create authenticated URL if PAT is available
        if pat_token:
            auth_url = create_authenticated_url(repo_url, pat_token)
            # Configure remote with authenticated URL
            if not configure_git_remote(auth_url, remote_name, verbose):
                return False
        else:
            # Configure remote without authentication
            if not configure_git_remote(repo_url, remote_name, verbose):
                return False

        # Push the branch
        if verbose:
            print(f"Pushar branch '{branch_name}' till remote '{remote_name}'...")

        result = subprocess.run(['git', 'push', remote_name, branch_name],
                                capture_output=True, text=True, timeout=GIT_TIMEOUT)

        if result.returncode == 0:
            if verbose:
                print(f"Lyckades pusha branch '{branch_name}' till {repo_url}")
            return True
        else:
            print(f"Push misslyckades med exit code {result.returncode}")
            if result.stdout:
                print(f"Git stdout: {result.stdout}")
            if result.stderr:
                print(f"Git stderr: {result.stderr}")
            return False

    except subprocess.CalledProcessError as e:
        print(f"Fel vid push till target repository: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
        return False
