#!/usr/bin/env python3
"""
Sync environment variables from .env file to config.yaml for Ray Serve deployment.

This script:
1. Creates config.yaml from config.yaml.template if it doesn't exist
2. Substitutes ${VAR_NAME} placeholders with actual environment variable values
3. Ensures all applications have access to required environment variables
"""

import os
import re
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


def ensure_config_yaml_exists():
    """Create config.yaml from template if it doesn't exist."""
    config_path = Path("config.yaml")
    template_path = Path("config.yaml.template")

    if not template_path.exists():
        print("❌ config.yaml.template not found")
        sys.exit(1)

    # Always copy template to ensure we have latest structure
    shutil.copy2(template_path, config_path)
    print("✅ Created config.yaml from template")

    return config_path


def substitute_env_vars(value):
    """Substitute ${VAR_NAME} placeholders with environment variable values."""
    if not isinstance(value, str):
        return value
    
    # Find all ${VAR_NAME} patterns
    pattern = re.compile(r'\$\{([^}]+)\}')
    
    def replacer(match):
        var_name = match.group(1)
        env_value = os.getenv(var_name)
        if env_value is None:
            print(f"⚠️  Warning: Environment variable {var_name} not found")
            return match.group(0)  # Keep the placeholder
        return env_value
    
    return pattern.sub(replacer, value)


def process_env_vars(env_vars_dict):
    """Process all environment variables in a dictionary, substituting placeholders."""
    processed = {}
    for key, value in env_vars_dict.items():
        processed[key] = substitute_env_vars(value)
    return processed


def validate_config_values(config):
    """Check for placeholder values that need to be replaced."""
    warnings = []

    if "applications" in config and config["applications"]:
        for app in config["applications"]:
            app_name = app.get("name", "unknown")
            if "runtime_env" in app and "env_vars" in app["runtime_env"]:
                env_vars = app["runtime_env"]["env_vars"]

                # Check for unsubstituted placeholders
                for key, value in env_vars.items():
                    if isinstance(value, str) and "${" in value:
                        warnings.append(f"⚠️  {app_name}: {key} contains unresolved placeholder: {value}")
                    
                    # Check for common placeholder patterns
                    placeholder_patterns = [
                        "your-api-key-here",
                        "your-openai-api-key-here",
                        "your-anthropic-api-key-here",
                        "your-langfuse-public-key-here",
                        "your-langfuse-secret-key-here",
                    ]
                    
                    if any(pattern in str(value) for pattern in placeholder_patterns):
                        warnings.append(f"⚠️  {app_name}: {key} contains placeholder value")

    if warnings:
        print("\n🔧 Configuration warnings:")
        for warning in warnings[:10]:  # Show first 10 warnings
            print(f"   {warning}")
        if len(warnings) > 10:
            print(f"   ... and {len(warnings) - 10} more")
        print("\n💡 Make sure these environment variables are set in your .env file")

    return warnings


def update_config_yaml():
    """Update config.yaml with environment variables."""
    config_path = ensure_config_yaml_exists()

    # Load the config
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Process each application
    if "applications" in config and config["applications"]:
        for app in config["applications"]:
            app_name = app.get("name", "unknown")
            
            # Process environment variables
            if "runtime_env" in app and "env_vars" in app["runtime_env"]:
                app["runtime_env"]["env_vars"] = process_env_vars(app["runtime_env"]["env_vars"])
                print(f"✅ Processed environment variables for {app_name}")

    # Write updated config
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"✅ Updated {config_path}")

    # Validate configuration values
    validate_config_values(config)

    return config_path


def check_critical_env_vars():
    """Check that critical environment variables are set."""
    critical_vars = {
        "OPENAI_API_KEY": "OpenAI API access (for chat server)",
        "ANTHROPIC_API_KEY": "Anthropic Claude API access (for data ingestion)",
        "NEO4J_URI": "Neo4j database connection",
        "NEO4J_PASSWORD": "Neo4j authentication",
    }
    
    missing = []
    for var, description in critical_vars.items():
        if not os.getenv(var):
            missing.append(f"  - {var}: {description}")
    
    if missing:
        print("\n⚠️  Missing critical environment variables:")
        for item in missing:
            print(item)
        print("\n💡 Set these in your .env file for full functionality")


def main():
    """Main function to sync environment variables to config.yaml."""
    print("🔄 Syncing environment variables to config.yaml...")

    # Load .env file
    load_env_file()

    # Check critical environment variables
    check_critical_env_vars()

    # Update config.yaml
    config_path = update_config_yaml()

    print(
        f"""
✅ Environment sync complete!

📋 Summary:
- Loaded variables from .env
- Updated {config_path}
- Substituted environment variable placeholders

🚀 Next steps:
- Run: just start (to launch all services)
- Run: just redeploy (to update after code changes)

💡 This sync is automatically run by deployment commands
"""
    )


if __name__ == "__main__":
    main()