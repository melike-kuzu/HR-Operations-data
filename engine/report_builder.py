from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from engine.master_dataset import MasterData

from engine.reports.project_tracker import build_project_tracker
from engine.reports.consultant_tracker import build_consultant_tracker
from engine.reports.utilisation import build_utilisation
from engine.reports.bench_status import build_bench_status
from engine.reports.partial_assignments import (
    build_partial_assignments,
)


@dataclass
class ReportBuilder:

    data: MasterData

    def build_all(self) -> dict[str, pd.DataFrame]:

        reports = {}

        reports["project_tracker"] = build_project_tracker(
            self.data
        )

        reports["consultant_tracker"] = build_consultant_tracker(
            self.data
        )

        reports["utilisation"] = build_utilisation(
            self.data
        )

        reports["bench_status"] = build_bench_status(
            self.data
        )

        reports["partial_assignments"] = (
            build_partial_assignments(
                self.data
            )
        )

        return reports