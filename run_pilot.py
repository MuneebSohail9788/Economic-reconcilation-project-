from pathlib import Path

from app.pilot.runner import run_controlled_pilot


if __name__ == "__main__":
    fixture_dir = Path(__file__).resolve().parents[1] / "tests" / "pilot_fixtures"
    report = run_controlled_pilot(fixture_dir)
    print("CONTROLLED PILOT: PASS")
    print(f"analysis_id={report.analysis_id}")
    print(f"finding_id={report.finding_id}")
    print(f"status={report.status}")
    print(f"reconciliation_status={report.reconciliation_status.value}")
    print(f"expected={report.expected}")
    print(f"captured={report.captured}")
    print(f"difference={report.difference}")
    print(f"documents_parsed={report.documents_parsed}")
    print(f"facts_extracted={report.facts_extracted}")
