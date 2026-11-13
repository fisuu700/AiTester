"""Génération des rapports unifiés (JSON) : résultats tri-couche, anomalies,
root cause analysis et références des captures d'écran."""

from __future__ import annotations

import json
import os

from app.schemas import RunReport


class ReportGenerator:
    def __init__(self, reports_dir: str) -> None:
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)

    def save(self, report: RunReport) -> str:
        path = os.path.join(self.reports_dir, f"report_{report.run_id}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(report.model_dump(mode="json"), fh, ensure_ascii=False, indent=2, default=str)
        return path

    def load(self, run_id: str) -> RunReport | None:
        path = os.path.join(self.reports_dir, f"report_{run_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as fh:
            return RunReport.model_validate(json.load(fh))

    def list_reports(self) -> list[dict]:
        reports = []
        if not os.path.isdir(self.reports_dir):
            return reports
        for name in sorted(os.listdir(self.reports_dir), reverse=True):
            if not name.startswith("report_") or not name.endswith(".json"):
                continue
            path = os.path.join(self.reports_dir, name)
            try:
                with open(path, encoding="utf-8") as fh:
                    data = json.load(fh)
                reports.append(
                    {
                        "run_id": data.get("run_id"),
                        "target_url": data.get("target_url"),
                        "scenario": data.get("scenario"),
                        "started_at": data.get("started_at"),
                        "success": data.get("success"),
                        "steps_count": len(data.get("steps") or []),
                        "anomalies_count": len(data.get("anomalies") or []),
                    }
                )
            except (json.JSONDecodeError, OSError):
                continue
        return reports
