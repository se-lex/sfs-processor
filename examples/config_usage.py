#!/usr/bin/env python3
"""
Example demonstrating how to use the centralized configuration system.
"""

from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_config, Config, load_config_from_file, reset_config


def example_basic_usage():
    """Example: Basic configuration usage."""
    print("=" * 60)
    print("Example 1: Basic Configuration Usage")
    print("=" * 60)

    # Get configuration (from environment variables + defaults)
    config = get_config()

    # Access configuration values
    print(f"Git minimum year: {config.git.min_year}")
    print(f"Git target repo: {config.git.target_repo}")
    print(f"API timeout: {config.api.rkrattsbaser_timeout}s")
    print(f"Internal links base: {config.links.internal_links_base_url}")
    print()


def example_validation():
    """Example: Validate configuration and show warnings."""
    print("=" * 60)
    print("Example 2: Configuration Validation")
    print("=" * 60)

    config = get_config()
    warnings = config.validate()

    if warnings:
        print("Configuration warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("✓ No configuration warnings")
    print()


def example_cloudflare_check():
    """Example: Check Cloudflare R2 configuration."""
    print("=" * 60)
    print("Example 3: Cloudflare R2 Configuration")
    print("=" * 60)

    config = get_config()

    if config.cloudflare.is_configured:
        print("✓ Cloudflare R2 is configured")
        print(f"  Endpoint: {config.cloudflare.endpoint_url}")
        print(f"  Bucket: {config.cloudflare.bucket_name}")
    else:
        print("✗ Cloudflare R2 is not fully configured")
        print("  Set these environment variables:")
        print("  - CLOUDFLARE_R2_ACCESS_KEY_ID")
        print("  - CLOUDFLARE_R2_SECRET_ACCESS_KEY")
        print("  - CLOUDFLARE_R2_BUCKET_NAME")
        print("  - CLOUDFLARE_R2_ACCOUNT_ID")
    print()


def example_programmatic_config():
    """Example: Create configuration programmatically."""
    print("=" * 60)
    print("Example 4: Programmatic Configuration")
    print("=" * 60)

    # Create custom configuration
    from config import GitConfig, APIConfig

    custom_config = Config(
        git=GitConfig(min_year=1990, timeout=300),
        api=APIConfig(rkrattsbaser_timeout=60)
    )

    print(f"Custom git min year: {custom_config.git.min_year}")
    print(f"Custom git timeout: {custom_config.git.timeout}s")
    print(f"Custom API timeout: {custom_config.api.rkrattsbaser_timeout}s")
    print()


def example_from_dict():
    """Example: Load configuration from dictionary."""
    print("=" * 60)
    print("Example 5: Load from Dictionary")
    print("=" * 60)

    config_dict = {
        "git": {
            "min_year": 1995,
            "timeout": 450
        },
        "processing": {
            "default_formats": ["md", "html"],
            "strict_validation": True
        }
    }

    config = Config.from_dict(config_dict)

    print(f"Git min year: {config.git.min_year}")
    print(f"Git timeout: {config.git.timeout}s")
    print(f"Default formats: {config.processing.default_formats}")
    print(f"Strict validation: {config.processing.strict_validation}")
    print()


def example_string_representation():
    """Example: Print configuration overview."""
    print("=" * 60)
    print("Example 6: Configuration String Representation")
    print("=" * 60)

    config = get_config()
    print(config)


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("SFS Processor - Configuration Examples")
    print("=" * 60 + "\n")

    example_basic_usage()
    example_validation()
    example_cloudflare_check()
    example_programmatic_config()
    example_from_dict()
    example_string_representation()

    print("=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
