#!/usr/bin/env python3
"""
Centralized configuration management for SFS Processor.

This module provides a single source of truth for all configuration values,
supporting environment variables, default values, and optional config files.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class APIConfig:
    """Configuration for external API endpoints."""

    # Regeringskansliet API
    rkrattsbaser_url: str = "https://beta.rkrattsbaser.gov.se/elasticsearch/SearchEsByRawJson"
    rkrattsbaser_timeout: int = 30

    # Riksdagen API
    riksdagen_base_url: str = "https://data.riksdagen.se"
    riksdagen_timeout: int = 30

    # EUR-Lex API
    eur_lex_base_url: str = "https://eur-lex.europa.eu"
    eur_lex_timeout: int = 30

    # PDF URL domains
    pdf_old_domain: str = "https://rkrattsdb.gov.se"
    pdf_new_domain: str = "https://svenskforfattningssamling.se"
    pdf_check_timeout: int = 10


@dataclass
class GitConfig:
    """Configuration for Git operations."""

    # Git repository settings
    default_target_repo: str = "https://github.com/se-lex/sfs.git"
    target_repo: Optional[str] = None
    github_pat: Optional[str] = None

    # Git commit settings
    min_year: int = 1980
    timeout: int = 600
    main_branch: str = "main"

    def __post_init__(self):
        """Load values from environment variables."""
        self.target_repo = os.getenv('GIT_TARGET_REPO', self.default_target_repo)
        self.github_pat = os.getenv('GIT_GITHUB_PAT')


@dataclass
class CloudflareConfig:
    """Configuration for Cloudflare R2 storage."""

    access_key_id: Optional[str] = None
    secret_access_key: Optional[str] = None
    bucket_name: Optional[str] = None
    account_id: Optional[str] = None

    def __post_init__(self):
        """Load values from environment variables."""
        self.access_key_id = os.getenv('CLOUDFLARE_R2_ACCESS_KEY_ID')
        self.secret_access_key = os.getenv('CLOUDFLARE_R2_SECRET_ACCESS_KEY')
        self.bucket_name = os.getenv('CLOUDFLARE_R2_BUCKET_NAME')
        self.account_id = os.getenv('CLOUDFLARE_R2_ACCOUNT_ID')

    @property
    def is_configured(self) -> bool:
        """Check if all required Cloudflare credentials are set."""
        return all([
            self.access_key_id,
            self.secret_access_key,
            self.bucket_name,
            self.account_id
        ])

    @property
    def endpoint_url(self) -> Optional[str]:
        """Get the R2 endpoint URL."""
        if self.account_id:
            return f"https://{self.account_id}.r2.cloudflarestorage.com"
        return None


@dataclass
class PathConfig:
    """Configuration for file paths and directories."""

    # Default paths
    default_input_dir: Path = Path("data/sfs-docs")
    default_output_dir: Path = Path("output")

    # Data paths
    data_dir: Path = Path("data")
    law_names_file: Path = Path("data/law-names.json")
    schema_file: Path = Path("data/sfs_document_schema.json")
    test_doc_ids_file: Path = Path("data/test-doc-ids.json")


@dataclass
class LinkConfig:
    """Configuration for link generation."""

    # Internal links base URL
    internal_links_base_url: str = "https://selex.se/eli"

    # ELI host
    eli_host: str = "selex.se"

    def __post_init__(self):
        """Load values from environment variables."""
        self.internal_links_base_url = os.getenv(
            'INTERNAL_LINKS_BASE_URL',
            self.internal_links_base_url
        )
        self.eli_host = os.getenv('ELI_HOST', self.eli_host)


@dataclass
class ProcessingConfig:
    """Configuration for document processing."""

    # Default output formats
    default_formats: list = field(default_factory=lambda: ["md"])

    # Processing flags
    default_year_as_folder: bool = True
    default_verbose: bool = False
    default_fetch_predocs: bool = False
    default_apply_links: bool = True

    # Validation settings
    strict_validation: bool = False


@dataclass
class Config:
    """Main configuration class that aggregates all configuration sections."""

    api: APIConfig = field(default_factory=APIConfig)
    git: GitConfig = field(default_factory=GitConfig)
    cloudflare: CloudflareConfig = field(default_factory=CloudflareConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    links: LinkConfig = field(default_factory=LinkConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)

    @classmethod
    def from_env(cls) -> "Config":
        """
        Create configuration from environment variables.

        Returns:
            Config: Configured instance with values from environment

        Example:
            >>> config = Config.from_env()
            >>> print(config.git.target_repo)
        """
        return cls(
            api=APIConfig(),
            git=GitConfig(),
            cloudflare=CloudflareConfig(),
            paths=PathConfig(),
            links=LinkConfig(),
            processing=ProcessingConfig()
        )

    @classmethod
    def from_dict(cls, config_dict: dict) -> "Config":
        """
        Create configuration from dictionary.

        Args:
            config_dict: Dictionary with configuration values

        Returns:
            Config: Configured instance

        Example:
            >>> config = Config.from_dict({"git": {"min_year": 1990}})
        """
        return cls(
            api=APIConfig(**config_dict.get('api', {})),
            git=GitConfig(**config_dict.get('git', {})),
            cloudflare=CloudflareConfig(**config_dict.get('cloudflare', {})),
            paths=PathConfig(**config_dict.get('paths', {})),
            links=LinkConfig(**config_dict.get('links', {})),
            processing=ProcessingConfig(**config_dict.get('processing', {}))
        )

    def validate(self) -> list:
        """
        Validate configuration and return list of warnings.

        Returns:
            list: List of warning messages

        Example:
            >>> config = Config.from_env()
            >>> warnings = config.validate()
            >>> if warnings:
            ...     print("Configuration warnings:", warnings)
        """
        warnings = []

        # Check Git configuration
        if not self.git.github_pat and 'github.com' in self.git.target_repo:
            warnings.append(
                "GIT_GITHUB_PAT not set - pushing to GitHub may require authentication"
            )

        # Check Cloudflare configuration
        if not self.cloudflare.is_configured:
            warnings.append(
                "Cloudflare R2 credentials not fully configured - upload features disabled"
            )

        # Check paths
        if not self.paths.law_names_file.exists():
            warnings.append(
                f"Law names file not found: {self.paths.law_names_file}"
            )

        if not self.paths.schema_file.exists():
            warnings.append(
                f"Schema file not found: {self.paths.schema_file}"
            )

        return warnings

    def __str__(self) -> str:
        """Return string representation of configuration (safe for logging)."""
        return f"""Config(
  API:
    - rkrattsbaser_url: {self.api.rkrattsbaser_url}
    - riksdagen_base_url: {self.api.riksdagen_base_url}
    - timeouts: {self.api.rkrattsbaser_timeout}s
  Git:
    - target_repo: {self.git.target_repo}
    - min_year: {self.git.min_year}
    - main_branch: {self.git.main_branch}
    - PAT configured: {'Yes' if self.git.github_pat else 'No'}
  Cloudflare:
    - configured: {'Yes' if self.cloudflare.is_configured else 'No'}
    - bucket: {self.cloudflare.bucket_name or 'Not set'}
  Links:
    - internal_base: {self.links.internal_links_base_url}
    - eli_host: {self.links.eli_host}
  Processing:
    - default_formats: {self.processing.default_formats}
    - strict_validation: {self.processing.strict_validation}
)"""


# Global configuration instance
_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get the global configuration instance.

    Creates the configuration from environment variables on first call,
    then returns the cached instance on subsequent calls.

    Returns:
        Config: The global configuration instance

    Example:
        >>> from config import get_config
        >>> config = get_config()
        >>> print(config.git.min_year)
        1980
    """
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config


def reset_config():
    """
    Reset the global configuration instance.

    Useful for testing or when environment variables have changed.

    Example:
        >>> reset_config()
        >>> config = get_config()  # Will reload from environment
    """
    global _config
    _config = None


def load_config_from_file(config_file: Path) -> Config:
    """
    Load configuration from a YAML or JSON file.

    Args:
        config_file: Path to configuration file

    Returns:
        Config: Configuration loaded from file

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config file format is invalid

    Example:
        >>> config = load_config_from_file(Path("config.yaml"))
    """
    import json

    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_file}")

    suffix = config_file.suffix.lower()

    if suffix == '.json':
        with open(config_file, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
    elif suffix in ['.yaml', '.yml']:
        try:
            import yaml
            with open(config_file, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f)
        except ImportError:
            raise ValueError("PyYAML is required to load YAML config files")
    else:
        raise ValueError(f"Unsupported config file format: {suffix}")

    return Config.from_dict(config_dict)
