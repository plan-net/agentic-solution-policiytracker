#!/usr/bin/env python3
"""
Sync environment variables from .env file to config.yaml for Kodosumi deployment.

This script:
1. Creates config.yaml from config.yaml.template if it doesn't exist
2. Syncs environment variables from .env to config.yaml
3. Ensures Ray workers have access to all environment variables
"""

import os
import shutil
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv


def load_env_file():
    """Load environment variables from .env file."""
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found. Please create one from .env.template")
        sys.exit(1)

    load_dotenv(env_path)
    print(f"✅ Loaded environment variables from {env_path}")
    return env_path


def get_relevant_env_vars():
    """Get environment variables that should be passed to Ray workers."""
    # Define which environment variables should be passed to workers
    relevant_vars = [
        # Core Configuration
        "LOG_LEVEL",
        "LOG_FORMAT",
        "ENVIRONMENT",
        # Storage Configuration
        "USE_AZURE_STORAGE",
        "AZURE_STORAGE_CONNECTION_STRING",
        "DEFAULT_INPUT_FOLDER",
        "DEFAULT_OUTPUT_FOLDER",
        "DEFAULT_CONTEXT_FOLDER",
        # Azure Storage Paths
        "AZURE_JOB_ID",
        "AZURE_INPUT_PATH",
        "AZURE_CONTEXT_PATH",
        "AZURE_OUTPUT_PATH",
        # LLM Configuration
        "LLM_ENABLED",
        "LLM_PROVIDER",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "OPENAI_MAX_TOKENS",
        "OPENAI_TEMPERATURE",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL",
        "ANTHROPIC_MAX_TOKENS",
        "ANTHROPIC_TEMPERATURE",
        "LLM_MAX_CONCURRENT",
        "LLM_TIMEOUT_SECONDS",
        "LLM_FALLBACK_ENABLED",
        # Langfuse Configuration
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        # Processing Configuration
        "MAX_BATCH_SIZE",
        "PROCESSING_TIMEOUT_SECONDS",
        "MAX_DOCUMENT_SIZE_MB",
        "CONFIDENCE_THRESHOLD",
        "PRIORITY_THRESHOLD",
        # Ray Configuration
        "RAY_ADDRESS",
        "RAY_NUM_CPUS",
        "RAY_TASK_MAX_RETRIES",
        "RAY_TASK_TIMEOUT_SECONDS",
        # Performance
        "ENABLE_PERFORMANCE_LOGGING",
    ]

    env_vars = {}
    missing_vars = []

    for var in relevant_vars:
        value = os.getenv(var)
        if value is not None:
            env_vars[var] = value
        else:
            missing_vars.append(var)

    print(f"✅ Found {len(env_vars)} environment variables")
    if missing_vars:
        print(f"⚠️  Missing variables (will use defaults): {', '.join(missing_vars[:5])}")
        if len(missing_vars) > 5:
            print(f"   ... and {len(missing_vars) - 5} more")

    return env_vars


def validate_config_values(config):
    """Check for placeholder values that need to be replaced."""
    warnings = []

    if "applications" in config and config["applications"]:
        app = config["applications"][0]
        if "runtime_env" in app and "env_vars" in app["runtime_env"]:
            env_vars = app["runtime_env"]["env_vars"]

            # Check for placeholder API keys
            placeholder_patterns = [
                "your-api-key-here",
                "your-openai-api-key-here",
                "your-anthropic-api-key-here",
                "your-langfuse-public-key-here",
                "your-langfuse-secret-key-here",
                "placeholder-",
            ]

            for key, value in env_vars.items():
                if any(pattern in str(value) for pattern in placeholder_patterns):
                    warnings.append(f"⚠️  {key} contains placeholder value: {value}")

    if warnings:
        print("\n🔧 Configuration warnings:")
        for warning in warnings[:5]:  # Show first 5 warnings
            print(f"   {warning}")
        if len(warnings) > 5:
            print(f"   ... and {len(warnings) - 5} more placeholder values")
        print("\n💡 Update these values in your .env file or config.yaml for full functionality")

    return warnings


def ensure_config_yaml_exists():
    """Create config.yaml from template if it doesn't exist."""
    config_path = Path("config.yaml")
    template_path = Path("config.yaml.template")

    if config_path.exists():
        print("✅ config.yaml already exists")
        return config_path

    if not template_path.exists():
        print("❌ config.yaml.template not found")
        sys.exit(1)

    # Copy template to config.yaml
    shutil.copy2(template_path, config_path)
    print("✅ Created config.yaml from template")
    print("⚠️  Remember to update API keys and other secrets in config.yaml")

    return config_path


def update_config_yaml(env_vars):
    """Update config.yaml with environment variables."""
    config_path = ensure_config_yaml_exists()

    # Load existing config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Find the application entry
    if "applications" not in config or not config["applications"]:
        print("❌ No applications found in config.yaml")
        sys.exit(1)

    app = config["applications"][0]  # Assuming single application

    # Ensure runtime_env exists
    if "runtime_env" not in app:
        app["runtime_env"] = {}

    if "env_vars" not in app["runtime_env"]:
        app["runtime_env"]["env_vars"] = {}

    # Add required static variables
    static_vars = {
        "PYTHONPATH": ".",
    }

    # Merge static and environment variables
    all_vars = {**static_vars, **env_vars}

    # Update environment variables
    app["runtime_env"]["env_vars"].update(all_vars)

    # Write updated config
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Updated config.yaml with {len(all_vars)} environment variables")

    # Validate configuration values
    validate_config_values(config)

    return config_path


def main():
    """Main function to sync environment variables to config.yaml."""
    print("🔄 Syncing environment variables to config.yaml...")

    # Load .env file
    load_env_file()

    # Get relevant environment variables
    env_vars = get_relevant_env_vars()

    # Update config.yaml
    config_path = update_config_yaml(env_vars)

    print(
        f"""
✅ Environment sync complete!

📋 Summary:
- Loaded variables from .env
- Updated {config_path}
- Ray workers will now have access to environment variables

🚀 Next steps:
- Run: just dev-quick
- Test your deployment

💡 This sync is automatically run by 'just dev' and 'just dev-quick'
"""
    )


if __name__ == "__main__":
    main()
