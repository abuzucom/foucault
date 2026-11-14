#!/usr/bin/env python3
"""The shipped provider registry selects the reviewed active model."""

from __future__ import annotations

import unittest

from ci import call_model

ACTIVE_MODEL = "minimax-m3.1-flash"
RETIRED_MODEL = "kimi-k2.7-code"


class ShippedProviderRegistryTests(unittest.TestCase):
    """Pin the active review profile that ci/model_providers.json ships."""

    def test_active_profile_uses_the_reviewed_model(self):
        # kimi-k2.7-code broke the report format contract on every observed
        # review. The active profile moved to the large-context profile.
        profile = call_model._load_profile()
        self.assertEqual(profile["model"], ACTIVE_MODEL)
        self.assertEqual(profile["protocol"], "ollama")

    def test_typical_review_input_selects_the_active_profile(self):
        profile = call_model.select_profile(estimated_tokens=50_000)
        self.assertEqual(profile["model"], ACTIVE_MODEL)

    def test_registry_ships_no_retired_model(self):
        config = call_model._load_config()
        models = [profile["model"] for profile in config["providers"].values()]
        self.assertNotIn(RETIRED_MODEL, models)

    def test_registry_ships_no_large_input_route(self):
        # The active profile already holds the largest context. A route to
        # itself adds no capacity. Adopter registries may still set the key.
        self.assertNotIn("large_input_provider", call_model._load_config())
        self.assertIsNone(call_model._large_profile())


if __name__ == "__main__":
    unittest.main()
