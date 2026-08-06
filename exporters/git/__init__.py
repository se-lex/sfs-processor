"""Git export functionality for SFS documents."""

from .generate_commits import (
    InitCommitPlan,
    TemporalCommitPlan,
    create_init_git_commit,
    plan_init_commit,
    plan_temporal_commits,
)
from .git_utils import (
    check_duplicate_commit_message,
    clone_target_repository_to_temp,
    configure_git_remote,
    create_commit_with_date,
    get_target_repository,
    has_staged_changes,
    is_file_tracked,
    prepare_git_branch,
    push_to_target_repository,
    remove_all_commits_on_branch,
    restore_original_branch,
    stage_file,
)
from .init_commits_batch_processor import process_files_with_git_batch
from .temporal_commits_batch_processor import process_temporal_commits_batch

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
    'check_duplicate_commit_message',
    'create_commit_with_date',
    'process_files_with_git_batch',
    'process_temporal_commits_batch',
    'create_init_git_commit',
    'plan_init_commit',
    'plan_temporal_commits',
    'InitCommitPlan',
    'TemporalCommitPlan',
]
