import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.dart_filing_cleanup import (  # noqa: E402
    apply_dart_filing_duplicate_cleanup,
    build_dart_filing_duplicate_cleanup_plan,
    collect_active_dart_filing_items,
    recent_dart_manifest_tickers,
)
from research_os.rag_memory import (  # noqa: E402
    connect_rag_db,
    upsert_research_memory_document,
)


class DartFilingDuplicateCleanupTests(unittest.TestCase):
    def test_soft_archives_identical_sequence_copy_and_keeps_one_active_rag_document(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            vault = root / "research_vault"
            ticker_dir = vault / "300080"
            ticker_dir.mkdir(parents=True)
            canonical_name = "300080-dart-filing-watch-2026-08-11-20260811000013"
            duplicate_name = f"{canonical_name}-002"
            markdown = "# 플리토 DART 공시\n\n반기보고서 원문 확인 필요\n"
            payload = {
                "module": "dart_filing_watch",
                "ticker": "300080",
                "filing": {
                    "corp_name": "플리토",
                    "rcept_no": "20260811000013",
                    "receipt_date": "20260811",
                    "report_name": "반기보고서 (2026.06)",
                    "source_url": "https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20260811000013",
                },
                "tags": ["dart", "earnings"],
            }
            for name in (canonical_name, duplicate_name):
                (ticker_dir / f"{name}.md").write_text(markdown, encoding="utf-8")
                (ticker_dir / f"{name}.json").write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )

            duplicate_entry = {
                "ticker": "300080",
                "type": "dart-filing-watch",
                "date": "2026-08-11",
                "file_name": f"{duplicate_name}.md",
                "relative_path": f"research_vault/300080/{duplicate_name}.md",
                "json_file_name": f"{duplicate_name}.json",
                "json_relative_path": f"research_vault/300080/{duplicate_name}.json",
                "module": "dart_filing_watch",
                "summary": "플리토 DART 신규 공시: 반기보고서 (2026.06)",
                "source_type": "official_filing",
                "source_url": payload["filing"]["source_url"],
                "rcept_no": "20260811000013",
                "tags": ["dart", "earnings"],
            }
            (vault / "manifest.json").write_text(
                json.dumps([duplicate_entry], ensure_ascii=False, indent=2), encoding="utf-8"
            )
            upsert_research_memory_document(
                vault_dir=vault,
                entry=duplicate_entry,
                full_text=markdown,
            )

            plan = build_dart_filing_duplicate_cleanup_plan(vault)
            self.assertEqual(plan["duplicate_group_count"], 1)
            self.assertEqual(plan["duplicate_candidate_count"], 1)
            self.assertEqual(plan["skipped_group_count"], 0)
            self.assertEqual(collect_active_dart_filing_items(vault, tickers=set()), [])

            result = apply_dart_filing_duplicate_cleanup(vault, plan)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["canonical_upsert_count"], 1)
            self.assertEqual(result["archived_count"], 1)
            self.assertTrue((ticker_dir / f"{canonical_name}.md").exists())
            self.assertTrue((ticker_dir / f"{duplicate_name}.md").exists())

            archived_payload = json.loads((ticker_dir / f"{duplicate_name}.json").read_text(encoding="utf-8"))
            self.assertEqual(archived_payload["status"], "archived")
            self.assertTrue(archived_payload["is_deleted"])
            active_payload = json.loads((ticker_dir / f"{canonical_name}.json").read_text(encoding="utf-8"))
            self.assertFalse(active_payload.get("is_deleted", False))

            manifest = json.loads((vault / "manifest.json").read_text(encoding="utf-8"))
            active = [entry for entry in manifest if not entry.get("is_deleted")]
            archived = [entry for entry in manifest if entry.get("is_deleted")]
            self.assertEqual(len(active), 1)
            self.assertEqual(active[0]["file_name"], f"{canonical_name}.md")
            self.assertEqual(active[0]["tags"], ["dart", "earnings"])
            self.assertEqual(len(archived), 1)
            self.assertEqual(archived[0]["file_name"], f"{duplicate_name}.md")

            with connect_rag_db(vault) as connection:
                rows = connection.execute(
                    "SELECT source_relative_path FROM research_memory_documents"
                ).fetchall()
            self.assertEqual([row["source_relative_path"] for row in rows], [active[0]["relative_path"]])
            self.assertEqual(build_dart_filing_duplicate_cleanup_plan(vault)["duplicate_candidate_count"], 0)

    def test_content_mismatch_is_left_for_human_review(self):
        with TemporaryDirectory() as temporary:
            vault = Path(temporary) / "research_vault"
            ticker_dir = vault / "417030"
            ticker_dir.mkdir(parents=True)
            canonical_name = "417030-dart-filing-watch-2026-08-18-20260818000030"
            duplicate_name = f"{canonical_name}-002"
            payload = {
                "module": "dart_filing_watch",
                "ticker": "417030",
                "filing": {"rcept_no": "20260818000030", "receipt_date": "20260818"},
            }
            for name, markdown in ((canonical_name, "official copy"), (duplicate_name, "different copy")):
                (ticker_dir / f"{name}.md").write_text(markdown, encoding="utf-8")
                (ticker_dir / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")

            plan = build_dart_filing_duplicate_cleanup_plan(vault)
            self.assertEqual(plan["duplicate_candidate_count"], 0)
            self.assertEqual(plan["skipped_group_count"], 1)
            self.assertEqual(plan["skipped_groups"][0]["reason"], "content_hash_mismatch")

    def test_remark_prefix_refinement_reuses_complete_metadata_then_archives_duplicates(self):
        with TemporaryDirectory() as temporary:
            vault = Path(temporary) / "research_vault"
            ticker_dir = vault / "300080"
            ticker_dir.mkdir(parents=True)
            canonical_name = "300080-dart-filing-watch-2026-06-26-20260626901314"
            duplicate_name = f"{canonical_name}-002"
            markdown = "# DART 신규 공시 감시\n\n플리토 공시 본문\n"
            canonical_payload = {
                "module": "dart_filing_watch",
                "ticker": "300080",
                "filing": {
                    "rcept_no": "20260626901314",
                    "receipt_date": "20260626",
                    "report_name": "[기재정정]단일판매ㆍ공급계약체결",
                    "remark": "코",
                },
            }
            refined_payload = {
                **canonical_payload,
                "filing": {**canonical_payload["filing"], "remark": "코정"},
            }
            (ticker_dir / f"{canonical_name}.md").write_text(markdown, encoding="utf-8")
            (ticker_dir / f"{duplicate_name}.md").write_text(markdown, encoding="utf-8")
            (ticker_dir / f"{canonical_name}.json").write_text(
                json.dumps(canonical_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (ticker_dir / f"{duplicate_name}.json").write_text(
                json.dumps(refined_payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            plan = build_dart_filing_duplicate_cleanup_plan(vault)
            self.assertEqual(plan["duplicate_candidate_count"], 1)
            self.assertEqual(plan["skipped_group_count"], 0)
            refinement = plan["groups"][0]["metadata_refinement"]
            self.assertEqual(refinement["field"], "filing.remark")
            self.assertEqual(refinement["from_value"], "코")
            self.assertEqual(refinement["to_value"], "코정")

            result = apply_dart_filing_duplicate_cleanup(vault, plan)
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["metadata_refinement_count"], 1)
            active_payload = json.loads((ticker_dir / f"{canonical_name}.json").read_text(encoding="utf-8"))
            archived_payload = json.loads((ticker_dir / f"{duplicate_name}.json").read_text(encoding="utf-8"))
            self.assertEqual(active_payload["filing"]["remark"], "코정")
            self.assertTrue(archived_payload["is_deleted"])
            post_plan = build_dart_filing_duplicate_cleanup_plan(vault)
            self.assertEqual(post_plan["duplicate_candidate_count"], 0)
            self.assertEqual(post_plan["skipped_group_count"], 0)

    def test_recent_manifest_scope_does_not_scan_unrelated_historic_tickers(self):
        with TemporaryDirectory() as temporary:
            vault = Path(temporary) / "research_vault"
            ticker_dir = vault / "005930"
            ticker_dir.mkdir(parents=True)
            report = ticker_dir / "005930-dart-filing-watch-2026-08-26-20260826000001.md"
            report.write_text("DART", encoding="utf-8")
            (vault / "manifest.json").write_text(
                json.dumps(
                    [
                        {
                            "ticker": "005930",
                            "type": "dart-filing-watch",
                            "relative_path": "research_vault/005930/005930-dart-filing-watch-2026-08-26-20260826000001.md",
                        },
                        {
                            "ticker": "999999",
                            "type": "dart-filing-watch",
                            "relative_path": "research_vault/999999/missing.md",
                        },
                    ]
                ),
                encoding="utf-8",
            )
            self.assertEqual(recent_dart_manifest_tickers(vault, hours=1), {"005930"})
            self.assertEqual(recent_dart_manifest_tickers(vault, hours=1, max_tickers=0), set())
