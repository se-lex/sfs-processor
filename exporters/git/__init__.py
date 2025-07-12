"""Git export functionality for SFS documents."""

from .git_utils import (
    prepare_git_branch, 
    restore_original_branch, 
    remove_all_commits_on_branch,
    get_target_repository,
    configure_git_remote,
    push_to_target_repository,
    clone_target_repository_to_temp,
    is_file_tracked,
    has_staged_changes,
    stage_file,
    create_commit_with_date
)
from .batch_processor import process_files_with_git_batch
from .generate_commits import create_init_git_commit

__all__ = [
    'prepare_git_branch', 
    'restore_original_branch', 
    'remove_all_commits_on_branch',
    'get_target_repository',
    'configure_git_remote', 
    'push_to_target_repository',
    'clone_target_repository_to_temp',
    'is_file_tracked',
    'has_staged_changes',
    'stage_file',
    'create_commit_with_date',
    'process_files_with_git_batch',
    'create_init_git_commit'
]
