"""Compatibility facade for Beacon rule metadata.

The canonical implementation lives in ``beacon.engine.metadata_registry``.
Keep this module so existing CLI, reports, and external integrations that
import ``beacon.rules_registry`` continue to work during the Module 1 release.
"""

from beacon.engine.metadata_registry import get, list_rules, reload

__all__ = ["get", "list_rules", "reload"]
