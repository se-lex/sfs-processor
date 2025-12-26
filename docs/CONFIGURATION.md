# Configuration Management

## Overview

SFS Processor uses a centralized configuration system that supports:
- **Environment variables** for sensitive data and deployment-specific settings
- **Configuration files** (YAML/JSON) for non-sensitive defaults
- **Programmatic configuration** for testing and advanced use cases
- **Sensible defaults** for all settings

## Quick Start

### Using Environment Variables (Recommended for Production)

```bash
# Set required environment variables
export GIT_TARGET_REPO="https://github.com/your-org/your-repo.git"
export GIT_GITHUB_PAT="ghp_your_token_here"
export INTERNAL_LINKS_BASE_URL="https://your-domain.com/eli"

# Run processor
python sfs_processor.py --input data/sfs-docs --output output
```

### Using Configuration File

1. Copy the example configuration:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml` with your settings

3. Load configuration in your code:
   ```python
   from config import load_config_from_file
   config = load_config_from_file(Path("config.yaml"))
   ```

### Using Default Configuration

```python
from config import get_config

# Uses environment variables + defaults
config = get_config()

print(f"Git min year: {config.git.min_year}")
print(f"API timeout: {config.api.rkrattsbaser_timeout}")
```

## Configuration Sections

### API Configuration (`config.api`)

Settings for external API endpoints:

| Setting | Default | Description |
|---------|---------|-------------|
| `rkrattsbaser_url` | `https://beta.rkrattsbaser.gov.se/...` | Regeringskansliet API URL |
| `rkrattsbaser_timeout` | `30` | Request timeout in seconds |
| `riksdagen_base_url` | `https://data.riksdagen.se` | Riksdagen API base URL |
| `riksdagen_timeout` | `30` | Request timeout in seconds |
| `eur_lex_base_url` | `https://eur-lex.europa.eu` | EUR-Lex API base URL |
| `eur_lex_timeout` | `30` | Request timeout in seconds |
| `pdf_old_domain` | `https://rkrattsdb.gov.se` | Old PDF domain |
| `pdf_new_domain` | `https://svenskforfattningssamling.se` | New PDF domain |
| `pdf_check_timeout` | `10` | PDF URL check timeout |

**Example:**
```python
config = get_config()
timeout = config.api.rkrattsbaser_timeout  # 30
url = config.api.rkrattsbaser_url
```

### Git Configuration (`config.git`)

Settings for Git operations:

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `target_repo` | `GIT_TARGET_REPO` | `https://github.com/se-lex/sfs.git` | Git repository URL |
| `github_pat` | `GIT_GITHUB_PAT` | `None` | GitHub Personal Access Token |
| `min_year` | - | `1980` | Minimum year for git commits |
| `timeout` | - | `600` | Git operation timeout (seconds) |
| `main_branch` | - | `main` | Main branch name |

**Example:**
```python
config = get_config()
repo = config.git.target_repo
min_year = config.git.min_year  # 1980
```

### Cloudflare Configuration (`config.cloudflare`)

Settings for Cloudflare R2 storage:

| Setting | Environment Variable | Required |
|---------|---------------------|----------|
| `access_key_id` | `CLOUDFLARE_R2_ACCESS_KEY_ID` | Yes |
| `secret_access_key` | `CLOUDFLARE_R2_SECRET_ACCESS_KEY` | Yes |
| `bucket_name` | `CLOUDFLARE_R2_BUCKET_NAME` | Yes |
| `account_id` | `CLOUDFLARE_R2_ACCOUNT_ID` | Yes |

**Helper Properties:**
- `is_configured`: Returns `True` if all credentials are set
- `endpoint_url`: Returns the R2 endpoint URL

**Example:**
```python
config = get_config()

if config.cloudflare.is_configured:
    print(f"Uploading to: {config.cloudflare.endpoint_url}")
    print(f"Bucket: {config.cloudflare.bucket_name}")
else:
    print("Cloudflare R2 not configured")
```

### Link Configuration (`config.links`)

Settings for link generation:

| Setting | Environment Variable | Default | Description |
|---------|---------------------|---------|-------------|
| `internal_links_base_url` | `INTERNAL_LINKS_BASE_URL` | `https://selex.se/eli` | Base URL for internal links |
| `eli_host` | `ELI_HOST` | `selex.se` | ELI host for document identifiers |

**Example:**
```python
config = get_config()
base_url = config.links.internal_links_base_url
link = f"{base_url}/sfs/2010/800"
```

### Processing Configuration (`config.processing`)

Settings for document processing:

| Setting | Default | Description |
|---------|---------|-------------|
| `default_formats` | `["md"]` | Default output formats |
| `default_year_as_folder` | `True` | Create year subdirectories |
| `default_verbose` | `False` | Verbose output |
| `default_fetch_predocs` | `False` | Fetch förarbeten details |
| `default_apply_links` | `True` | Apply links in documents |
| `strict_validation` | `False` | Strict JSON schema validation |

**Example:**
```python
config = get_config()
formats = config.processing.default_formats  # ["md"]
strict = config.processing.strict_validation  # False
```

### Path Configuration (`config.paths`)

Settings for file paths:

| Setting | Default | Description |
|---------|---------|-------------|
| `default_input_dir` | `data/sfs-docs` | Default input directory |
| `default_output_dir` | `output` | Default output directory |
| `data_dir` | `data` | Data directory |
| `law_names_file` | `data/law-names.json` | Law names reference file |
| `schema_file` | `data/sfs_document_schema.json` | JSON schema file |

**Example:**
```python
config = get_config()
input_dir = config.paths.default_input_dir
schema = config.paths.schema_file
```

## Advanced Usage

### Validation

Check configuration and get warnings:

```python
from config import get_config

config = get_config()
warnings = config.validate()

if warnings:
    for warning in warnings:
        print(f"Warning: {warning}")
```

### Resetting Configuration

Useful for testing or when environment variables change:

```python
from config import reset_config, get_config

# Change environment variable
os.environ['GIT_TARGET_REPO'] = 'https://github.com/new-repo.git'

# Reset and reload
reset_config()
config = get_config()  # Will use new environment variable
```

### Loading from File

Load configuration from YAML or JSON file:

```python
from pathlib import Path
from config import load_config_from_file

config = load_config_from_file(Path("config.yaml"))
```

### Programmatic Configuration

Create configuration programmatically:

```python
from config import Config, GitConfig, APIConfig

config = Config(
    git=GitConfig(min_year=1990, timeout=300),
    api=APIConfig(rkrattsbaser_timeout=60)
)
```

### Using from_dict

Create configuration from dictionary:

```python
from config import Config

config_dict = {
    "git": {
        "min_year": 1990,
        "timeout": 300
    },
    "api": {
        "rkrattsbaser_timeout": 60
    }
}

config = Config.from_dict(config_dict)
```

## Environment Variable Reference

Complete list of supported environment variables:

| Variable | Used In | Description |
|----------|---------|-------------|
| `GIT_TARGET_REPO` | Git | Target git repository URL |
| `GIT_GITHUB_PAT` | Git | GitHub Personal Access Token |
| `CLOUDFLARE_R2_ACCESS_KEY_ID` | Cloudflare | R2 access key ID |
| `CLOUDFLARE_R2_SECRET_ACCESS_KEY` | Cloudflare | R2 secret access key |
| `CLOUDFLARE_R2_BUCKET_NAME` | Cloudflare | R2 bucket name |
| `CLOUDFLARE_R2_ACCOUNT_ID` | Cloudflare | R2 account ID |
| `INTERNAL_LINKS_BASE_URL` | Links | Base URL for internal links |
| `ELI_HOST` | Links | ELI host for identifiers |

## Best Practices

### Security

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive data (API keys, tokens, passwords)
3. **Use config files** only for non-sensitive defaults
4. **Add config files to .gitignore**: `config.yaml`, `config.json`

### Deployment

1. **Development**: Use `config.yaml` for local development settings
2. **CI/CD**: Use environment variables in GitHub Actions/workflows
3. **Production**: Use environment variables or secret management service

### Example .env file

Create a `.env` file (already in `.gitignore`):

```bash
# Git Configuration
GIT_TARGET_REPO=https://github.com/your-org/your-repo.git
GIT_GITHUB_PAT=ghp_your_token_here

# Cloudflare R2
CLOUDFLARE_R2_ACCESS_KEY_ID=your_access_key_id
CLOUDFLARE_R2_SECRET_ACCESS_KEY=your_secret_access_key
CLOUDFLARE_R2_BUCKET_NAME=your_bucket_name
CLOUDFLARE_R2_ACCOUNT_ID=your_account_id

# Links
INTERNAL_LINKS_BASE_URL=https://your-domain.com/eli
```

Load with python-dotenv:
```python
from dotenv import load_dotenv
load_dotenv()  # Loads .env file into environment

from config import get_config
config = get_config()  # Uses environment variables
```

## Migration Guide

### From Hardcoded Values

**Before:**
```python
MIN_GIT_YEAR = 1980
timeout = 30
url = "https://beta.rkrattsbaser.gov.se/..."
```

**After:**
```python
from config import get_config

config = get_config()
min_year = config.git.min_year
timeout = config.api.rkrattsbaser_timeout
url = config.api.rkrattsbaser_url
```

### From os.getenv() Calls

**Before:**
```python
repo = os.getenv('GIT_TARGET_REPO', 'https://github.com/default/repo.git')
base_url = os.getenv('INTERNAL_LINKS_BASE_URL', 'https://selex.se/eli')
```

**After:**
```python
from config import get_config

config = get_config()
repo = config.git.target_repo
base_url = config.links.internal_links_base_url
```

## Troubleshooting

### Configuration Not Loading

Check that environment variables are set:
```python
import os
print("GIT_TARGET_REPO:", os.getenv('GIT_TARGET_REPO'))
```

### Warnings on Startup

Run validation to see configuration issues:
```python
from config import get_config

config = get_config()
warnings = config.validate()
for w in warnings:
    print(w)
```

### Config File Not Found

Ensure config file path is correct:
```python
from pathlib import Path

config_file = Path("config.yaml")
print(f"Config file exists: {config_file.exists()}")
print(f"Absolute path: {config_file.absolute()}")
```

## See Also

- [JSON Schema Validation](JSON_SCHEMA_VALIDATION.md)
- [Environment Variables in .gitignore](../.gitignore)
- [Example Configuration](../config.example.yaml)
