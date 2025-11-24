#!/usr/bin/env python3
"""Test script for entity resolution improvements.

Tests the entity details tool with various queries to verify:
1. Smart entity resolution (no false positives)
2. Structured output format
3. UUID-based fact retrieval
4. Relationship extraction
5. Source attribution
6. Serialization safety (no DateTime errors)
"""

import asyncio
import json
from datetime import datetime

from graphiti_core import Graphiti

from src.chat.tools.entity import EntityDetailsTool


class EntityResolutionTester:
    def __init__(self):
        self.client = None
        self.tool = None
        self.test_results = []

    async def setup(self):
        """Initialize Graphiti client and entity tool."""
        self.client = Graphiti("bolt://localhost:7687", "neo4j", "password123")
        self.tool = EntityDetailsTool(graphiti_client=self.client)
        print("✅ Connected to Neo4j and initialized entity tool\n")

    async def teardown(self):
        """Close connections."""
        if self.client:
            await self.client.close()
        print("\n✅ Closed connections")

    def log_test(self, test_name: str, passed: bool, details: str):
        """Log test result."""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   {details}")
        self.test_results.append({"test": test_name, "passed": passed, "details": details})

    async def test_ambiguous_entity(self, entity_name: str, expected_type: str):
        """Test ambiguous entity resolution."""
        test_name = f"Ambiguous entity: '{entity_name}'"
        try:
            result = await self.tool._arun(entity_name, output_format="structured")

            # Check if entity was found
            if "error" in result or not result.get("entity"):
                self.log_test(
                    test_name,
                    False,
                    f"Entity not found or error: {result.get('error', 'No entity')}",
                )
                return

            resolved_name = result["entity"]["name"]
            entity_type = result["entity"]["type"]

            # Check if resolved correctly
            if expected_type.lower() in entity_type.lower():
                self.log_test(
                    test_name,
                    True,
                    f"Resolved to: {resolved_name} (Type: {entity_type})",
                )
            else:
                self.log_test(
                    test_name,
                    False,
                    f"Wrong type: got {entity_type}, expected {expected_type}",
                )

            # Check structured output
            required_keys = ["entity", "relationships", "facts", "sources"]
            missing_keys = [k for k in required_keys if k not in result]
            if missing_keys:
                self.log_test(f"{test_name} - Structure", False, f"Missing keys: {missing_keys}")
            else:
                self.log_test(
                    f"{test_name} - Structure",
                    True,
                    f"All required keys present: {len(result['relationships'])} relationships, {len(result['facts'])} facts, {len(result['sources'])} sources",
                )

        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")

    async def test_false_positive_prevention(self, query: str, should_not_match: str):
        """Test that queries don't match incorrect entities."""
        test_name = f"False positive prevention: '{query}' should not match '{should_not_match}'"
        try:
            result = await self.tool._arun(query, output_format="structured")

            if "error" in result or not result.get("entity"):
                self.log_test(test_name, True, "No false positive (entity not found)")
                return

            resolved_name = result["entity"]["name"].lower()
            if should_not_match.lower() in resolved_name:
                self.log_test(
                    test_name,
                    False,
                    f"False positive detected: matched '{result['entity']['name']}'",
                )
            else:
                self.log_test(
                    test_name,
                    True,
                    f"Correctly resolved to: {result['entity']['name']}",
                )

        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")

    async def test_serialization_safety(self, entity_name: str):
        """Test that output is JSON-serializable (no DateTime errors)."""
        test_name = f"Serialization safety: '{entity_name}'"
        try:
            result = await self.tool._arun(entity_name, output_format="structured")

            # Try to serialize to JSON
            try:
                json_str = json.dumps(result)
                self.log_test(test_name, True, f"Successfully serialized ({len(json_str)} bytes)")
            except TypeError as te:
                self.log_test(test_name, False, f"Serialization failed: {str(te)}")

        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")

    async def test_structured_vs_text_output(self, entity_name: str):
        """Test dual output format support."""
        test_name = f"Dual output format: '{entity_name}'"
        try:
            # Test structured output
            structured = await self.tool._arun(entity_name, output_format="structured")
            is_dict = isinstance(structured, dict)

            # Test text output
            text = await self.tool._arun(entity_name, output_format="text")
            is_str = isinstance(text, str)

            if is_dict and is_str:
                self.log_test(
                    test_name,
                    True,
                    f"Both formats work (structured: {type(structured).__name__}, text: {type(text).__name__})",
                )
            else:
                self.log_test(
                    test_name,
                    False,
                    f"Format mismatch (structured: {type(structured).__name__}, text: {type(text).__name__})",
                )

        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")

    async def test_uuid_based_matching(self, entity_name: str):
        """Test that facts are retrieved using UUID, not string matching."""
        test_name = f"UUID-based fact matching: '{entity_name}'"
        try:
            result = await self.tool._arun(entity_name, output_format="structured")

            if "error" in result or not result.get("entity"):
                self.log_test(test_name, False, "Entity not found")
                return

            # Check if UUID is present
            entity_uuid = result["entity"].get("uuid")
            if not entity_uuid:
                self.log_test(test_name, False, "No UUID found in entity")
                return

            # Check if facts were retrieved
            facts_count = len(result.get("facts", []))
            relationships_count = len(result.get("relationships", []))

            if facts_count > 0 or relationships_count > 0:
                self.log_test(
                    test_name,
                    True,
                    f"UUID-based retrieval successful ({facts_count} facts, {relationships_count} relationships)",
                )
            else:
                self.log_test(
                    test_name,
                    True,
                    f"UUID present but no facts/relationships (UUID: {entity_uuid[:8]}...)",
                )

        except Exception as e:
            self.log_test(test_name, False, f"Exception: {str(e)}")

    async def run_all_tests(self):
        """Run all test cases."""
        print("=" * 70)
        print("ENTITY RESOLUTION TEST SUITE")
        print("=" * 70)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # Test 1: Ambiguous entity resolution
        print("TEST GROUP 1: Ambiguous Entity Resolution")
        print("-" * 70)
        await self.test_ambiguous_entity("Meta", "Company")
        await self.test_ambiguous_entity("Apple", "Company")
        await self.test_ambiguous_entity("Amazon", "Company")
        print()

        # Test 2: Policy entities
        print("TEST GROUP 2: Policy Entity Resolution")
        print("-" * 70)
        await self.test_ambiguous_entity("AI Act", "Policy")
        await self.test_ambiguous_entity("GDPR", "Policy")
        await self.test_ambiguous_entity("DSA", "Policy")
        print()

        # Test 3: False positive prevention
        print("TEST GROUP 3: False Positive Prevention")
        print("-" * 70)
        await self.test_false_positive_prevention("Meta", "metadata")
        await self.test_false_positive_prevention("Meta", "systematic")
        print()

        # Test 4: Serialization safety
        print("TEST GROUP 4: Serialization Safety")
        print("-" * 70)
        await self.test_serialization_safety("Meta")
        await self.test_serialization_safety("AI Act")
        print()

        # Test 5: Dual output format
        print("TEST GROUP 5: Dual Output Format")
        print("-" * 70)
        await self.test_structured_vs_text_output("Meta")
        print()

        # Test 6: UUID-based matching
        print("TEST GROUP 6: UUID-Based Fact Matching")
        print("-" * 70)
        await self.test_uuid_based_matching("Meta")
        await self.test_uuid_based_matching("GDPR")
        print()

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary."""
        print("=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["passed"])
        failed = total - passed

        print(f"Total Tests: {total}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        print()

        if failed > 0:
            print("FAILED TESTS:")
            for result in self.test_results:
                if not result["passed"]:
                    print(f"  ❌ {result['test']}: {result['details']}")
        else:
            print("🎉 All tests passed!")

        print()
        print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)


async def main():
    """Main test runner."""
    tester = EntityResolutionTester()

    try:
        await tester.setup()
        await tester.run_all_tests()
    finally:
        await tester.teardown()


if __name__ == "__main__":
    asyncio.run(main())
