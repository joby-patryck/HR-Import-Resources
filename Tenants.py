"""
Tenant configuration loader.

Loads and validates tenant configurations from tenants.json with support for
case-insensitive tenant_id matching in CLI arguments and auto-enrollment logic.
"""
import json
from pathlib import Path

from resources import resource_path


def load_tenants() -> list[dict[str, str]]:
    """
    Load and validate tenant configurations from tenants.json.
    
    Locates tenants.json relative to this script file (not current working directory),
    parses the JSON, and returns a normalized list of tenant dictionaries with lowercase
    tenant_id values for case-insensitive CLI argument matching.
    
    The tenants.json file should contain a root "tenants" array with objects containing:
        - tenant_id (str): Required. Unique identifier for tenant (auto-lowercased)
        - business_unit_description (str): Business unit to match for user splitting
        - tenant_name (str): Human-readable tenant name
    
    Returns:
        List of tenant dictionaries with normalized keys and tenant_id in lowercase.
        Only includes tenants with non-empty tenant_id values.
        Returns empty list if no valid tenants found in config.
    
    Raises:
        FileNotFoundError: If tenants.json cannot be found in the script directory
        json.JSONDecodeError: If tenants.json is not valid JSON
    """
    # Resolve tenants.json relative to this module in development and to the
    # PyInstaller bundle (sys._MEIPASS) when running as a packaged app — never
    # the current working directory, which is unpredictable for a launched app.
    config_path: Path = resource_path("tenants.json")
    
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            config: dict = json.load(config_file)
    except FileNotFoundError:
        raise FileNotFoundError(f"tenants.json not found at {config_path}")

    # Extract the tenants array from config, safely defaulting to empty list if key missing
    tenants: list[dict] = config.get("tenants", [])
    
    # Build normalized tenant list with validated/filtered results:
    # - Only includes tenants with non-empty tenant_id (filters out incomplete configs)
    # - Converts tenant_id to lowercase for case-insensitive CLI argument matching
    # - Preserves all tenant fields with safe .get() defaults to prevent KeyError
    return [
        {
            "tenant_id": tenant.get("tenant_id", "").lower(),
            "business_unit_description": tenant.get("business_unit_description", ""),
            "tenant_name": tenant.get("tenant_name", ""),
        }
        for tenant in tenants
        if tenant.get("tenant_id")  # Only include tenants with a non-empty tenant_id field
    ]