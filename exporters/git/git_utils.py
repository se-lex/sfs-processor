"""Git utilities for SFS document processing."""

import subprocess
from datetime import datetime, date


def ensure_git_branch_for_commits(git_branch, remove_all_commits_first=True, verbose=False):
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
                              capture_output=True, text=True, check=True)
        current_branch = result.stdout.strip()

        # Generate commit branch name
        if "(date)" in git_branch:
            date_str = datetime.now().strftime("%Y%m%d")
            commit_branch = git_branch.replace("(date)", date_str)
        else:
            commit_branch = git_branch

        # Create and switch to the new branch
        subprocess.run(['git', 'checkout', '-b', commit_branch], 
                      check=True, capture_output=True)

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
                      check=True, capture_output=True)
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
                                  capture_output=True, text=True, check=True)
            original_branch = result.stdout.strip()
            
            # Switch to target branch if different
            if original_branch != branch_name:
                subprocess.run(['git', 'checkout', branch_name], 
                             check=True, capture_output=True)
        
        # Get the merge base with main branch (the point where current branch diverged)
        result = subprocess.run([
            'git', 'merge-base', 'HEAD', 'main'
        ], capture_output=True, text=True, check=True)
        
        merge_base = result.stdout.strip()
        
        # Find all commits on current branch since merge base
        result = subprocess.run([
            'git', 'log', 
            f'{merge_base}..HEAD',
            '--format=%H %s',
            '--reverse'  # Show oldest first
        ], capture_output=True, text=True, check=True)
        
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
                      check=True, capture_output=True)
        
        print(f"Tog bort {len(commits_to_remove)} commits från branchen")
        
        # Switch back to original branch if we switched
        if original_branch and original_branch != branch_name:
            subprocess.run(['git', 'checkout', original_branch], 
                         check=True, capture_output=True)
        
        return len(commits_to_remove)
        
    except subprocess.CalledProcessError as e:
        print(f"Varning: Kunde inte ta bort commits: {e}")
        if hasattr(e, 'stderr') and e.stderr:
            print(f"Git stderr: {e.stderr.decode('utf-8', errors='replace')}")
        return 0
    except FileNotFoundError:
        print("Varning: Git hittades inte.")
        return 0
