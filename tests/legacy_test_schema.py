"""Tests for schema versioning and migration."""
import json
from tools.schema import TestRun, AttackResult, SCHEMA_VERSION


class TestSchemaVersioning:
    """Tests for schema version handling."""

    def test_new_results_have_version(self):
        """New TestRun has current schema version."""
        run = TestRun()
        assert run.schema_version == SCHEMA_VERSION

    def test_roundtrip_serialization(self):
        """TestRun survives JSON roundtrip."""
        run = TestRun(
            provider="ollama",
            model="test",
            detector="substring",
            total_attacks=1,
            results=[
                AttackResult(
                    id="TEST-01",
                    name="Test",
                    category="test",
                    success=True,
                    confidence=0.9,
                    matched_indicators=["test"],
                    response_preview="test response",
                    time_ms=100,
                )
            ],
        )

        json_str = run.to_json()
        loaded = TestRun.from_dict(json.loads(json_str))

        assert loaded.provider == run.provider
        assert loaded.total_attacks == run.total_attacks
        assert len(loaded.results) == 1


class TestLegacyMigration:
    """Tests for migrating old result format."""

    def test_migrates_legacy_results(self):
        """v0 results are migrated to current schema."""
        legacy = {
            "timestamp": "2026-02-14T11:38:40.687977",
            "provider": "ollama/qwen2.5:3b",
            "detector": "substring",
            "total_attacks": 1,
            "successful": 1,
            "success_rate": 100.0,
            "categories": {"test": {"total": 1, "success": 1}},
            "results": [{
                "id": "TEST-01",
                "name": "Test",
                "category": "test",
                "success": True,
                "confidence": 0.9,
                "matched_indicators": ["test"],
                "response": "EXPLOITED here",
                "time_ms": 100,
                "reasoning": "Matched",
            }],
        }

        migrated = TestRun.from_dict(legacy)

        assert migrated.schema_version == SCHEMA_VERSION
        assert migrated.provider == "ollama"
        assert migrated.model == "qwen2.5:3b"
        assert "Migrated from legacy" in migrated.warnings[0]
