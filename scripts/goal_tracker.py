"""
Business Goals Tracker — Reads, parses, and tracks Business_Goals.md
Provides structured access to revenue targets, KPIs, projects, and bottlenecks.
Used by CEO Briefing system and task prioritization engine.
"""

import re
import yaml
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from dataclasses import dataclass, field

from config import config, FOLDERS, ensure_folders
from logger_setup import logger, audit_log


@dataclass
class RevenueTarget:
    period: str
    target: float
    actual: float
    progress_pct: float


@dataclass
class KPI:
    name: str
    target: str
    current: str
    status: str  # 🔴 🟡 🟢


@dataclass
class Project:
    name: str
    status: str
    start_date: str
    target_launch: str
    budget: float
    owner: str
    priority: str
    description: str


@dataclass
class Bottleneck:
    description: str
    impact: str
    mitigation: str


@dataclass
class BusinessGoals:
    """Parsed representation of Business_Goals.md."""
    metadata: dict = field(default_factory=dict)
    revenue_targets: list[RevenueTarget] = field(default_factory=list)
    kpis: list[KPI] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    bottlenecks: list[Bottleneck] = field(default_factory=list)
    quarterly_goals: dict[str, list[str]] = field(default_factory=dict)
    strategic_initiatives: list[str] = field(default_factory=list)
    raw_content: str = ""


class GoalTracker:
    """Reads and manages business goals from Business_Goals.md."""

    def __init__(self, goals_path: Path | None = None):
        self.goals_path = goals_path or config.business_goals_path
        ensure_folders()

    def load(self) -> BusinessGoals:
        """Parse Business_Goals.md into structured data."""
        goals = BusinessGoals()

        if not self.goals_path.exists():
            logger.warning(f"Business_Goals.md not found at {self.goals_path}")
            return goals

        try:
            content = self.goals_path.read_text(encoding="utf-8")
            goals.raw_content = content

            # Parse YAML frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    goals.metadata = yaml.safe_load(parts[1]) or {}

            # Parse revenue targets
            goals.revenue_targets = self._parse_revenue_targets(content)

            # Parse KPIs
            goals.kpis = self._parse_kpis(content)

            # Parse projects
            goals.projects = self._parse_projects(content)

            # Parse bottlenecks
            goals.bottlenecks = self._parse_bottlenecks(content)

            # Parse quarterly goals
            goals.quarterly_goals = self._parse_quarterly_goals(content)

            # Parse strategic initiatives
            goals.strategic_initiatives = self._parse_strategic_initiatives(content)

            logger.info(f"Business Goals loaded: {len(goals.projects)} projects, {len(goals.kpis)} KPIs")

        except Exception as e:
            logger.error(f"Failed to parse Business_Goals.md: {e}")

        return goals

    def update_kpi(self, kpi_name: str, current_value: str, status: str = "🟡"):
        """Update a KPI value in the file."""
        content = self.goals_path.read_text(encoding="utf-8")

        # Find the KPI line and update it
        pattern = rf"(\|\s*{re.escape(kpi_name)}\s*\|)\s*(\S+)\s*\|\s*(\S+)\s*\|(\s*\S+\s*\|)"
        replacement = rf"\1 \2 | {current_value} | {status} |"
        new_content = re.sub(pattern, replacement, content, flags=re.IGNORECASE)

        if new_content != content:
            self.goals_path.write_text(new_content, encoding="utf-8")
            logger.info(f"KPI updated: {kpi_name} = {current_value} ({status})")
            audit_log(
                action="kpi_updated",
                details={"kpi": kpi_name, "value": current_value, "status": status},
            )
        else:
            logger.warning(f"KPI not found for update: {kpi_name}")

    def update_revenue(self, period: str, actual: float):
        """Update actual revenue for a period."""
        content = self.goals_path.read_text(encoding="utf-8")

        # Parse the table to find the row
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if period.lower() in line.lower() and "|" in line:
                # Rebuild the row with new actual
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 4:
                    # Calculate progress
                    target_str = parts[1].replace("$", "").replace(",", "").strip()
                    try:
                        target = float(target_str)
                        progress = (actual / target * 100) if target > 0 else 0
                    except ValueError:
                        progress = 0

                    lines[i] = f"| {parts[0]} | {parts[1]} | ${actual:,.0f} | {progress:.0f}% |"
                    break

        self.goals_path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Revenue updated: {period} = ${actual:,.0f}")
        audit_log(
            action="revenue_updated",
            details={"period": period, "actual": actual},
        )

    def add_project(self, project: Project) -> bool:
        """Add a new project to the file."""
        content = self.goals_path.read_text(encoding="utf-8")

        # Find the Active Projects section end or insert before next major heading
        project_block = f"""
### {project.name}
- **Status:** {project.status}
- **Start Date:** {project.start_date}
- **Target Launch:** {project.target_launch}
- **Budget:** ${project.budget:,.0f}
- **Owner:** {project.owner}
- **Priority:** {project.priority}
- **Description:** {project.description}
"""
        # Insert before "## 📅 Quarterly Goals" or at end of projects section
        insert_marker = "## 📅 Quarterly Goals"
        if insert_marker in content:
            content = content.replace(insert_marker, project_block + "\n\n" + insert_marker)
        else:
            content += project_block

        self.goals_path.write_text(content, encoding="utf-8")
        logger.info(f"Project added: {project.name}")
        audit_log(action="project_added", details={"name": project.name})
        return True

    def get_overall_health(self) -> str:
        """Quick assessment of business health based on KPIs."""
        goals = self.load()
        if not goals.kpis:
            return "🟡 No data"

        red = sum(1 for k in goals.kpis if "🔴" in k.status)
        green = sum(1 for k in goals.kpis if "🟢" in k.status)
        total = len(goals.kpis)

        if red > total * 0.5:
            return "🔴 Critical — majority of KPIs off target"
        elif red > total * 0.25:
            return "🟡 Warning — some KPIs need attention"
        elif green > total * 0.7:
            return "🟢 Healthy — most KPIs on track"
        else:
            return "🟡 Mixed — review needed"

    # ─── Parsers ───────────────────────────────────────────────────────

    def _parse_revenue_targets(self, content: str) -> list[RevenueTarget]:
        """Parse revenue targets table."""
        targets = []
        in_table = False

        for line in content.split("\n"):
            if "Revenue Targets" in line or "revenue_target" in line.lower():
                in_table = True
                continue

            if in_table:
                if line.startswith("|") and "**" not in line and "---" not in line:
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 4:
                        try:
                            target_val = float(parts[1].replace("$", "").replace(",", "").strip())
                            actual_val = float(parts[2].replace("$", "").replace(",", "").strip())
                            progress_str = parts[3].replace("%", "").strip()
                            progress = float(progress_str) if progress_str not in ["0", ""] else 0

                            targets.append(RevenueTarget(
                                period=parts[0],
                                target=target_val,
                                actual=actual_val,
                                progress_pct=progress,
                            ))
                        except (ValueError, IndexError):
                            pass
                elif line.startswith("##") or line.startswith("---"):
                    in_table = False

        return targets

    def _parse_kpis(self, content: str) -> list[KPI]:
        """Parse KPI table."""
        kpis = []
        in_table = False

        for line in content.split("\n"):
            if "Key Performance Indicator" in line or "kpi" in line.lower():
                in_table = True
                continue

            if in_table:
                if line.startswith("|") and "---" not in line and "name" not in line.lower():
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 4 and not any(c.isdigit() for c in parts[0][:3]):
                        kpis.append(KPI(
                            name=parts[0],
                            target=parts[1],
                            current=parts[2],
                            status=parts[3] if len(parts) > 3 else "🟡",
                        ))
                elif line.startswith("##") or line.startswith("---"):
                    in_table = False

        return kpis

    def _parse_bottlenecks(self, content: str) -> list[Bottleneck]:
        """Parse bottlenecks table."""
        bottlenecks = []
        in_table = False

        for line in content.split("\n"):
            if "Bottleneck" in line or "bottleneck" in line.lower():
                in_table = True
                continue

            if in_table:
                if line.startswith("|") and "---" not in line and "description" not in line.lower():
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 3 and parts[0][0].isalpha():
                        bottlenecks.append(Bottleneck(
                            description=parts[0],
                            impact=parts[1],
                            mitigation=parts[2],
                        ))
                elif line.startswith("##"):
                    in_table = False

        return bottlenecks

    def _parse_projects(self, content: str) -> list[Project]:
        """Parse projects from markdown headings and bullet lists."""
        projects = []
        project_sections = re.findall(
            r"### (.*?)\n((?:- .*\n)+)",
            content,
            re.MULTILINE,
        )

        for name, bullets in project_sections:
            # Skip non-project sections
            if any(skip in name.lower() for skip in ["revenue stream", "known bottleneck", "strategic"]):
                continue

            project_data = {"name": name.strip()}
            for bullet in bullets.strip().split("\n"):
                match = re.match(r"- \*\*(\w[\w\s]*?):\*\*\s*(.*)", bullet)
                if match:
                    key = match.group(1).strip().lower().replace(" ", "_")
                    value = match.group(2).strip()
                    if key == "budget":
                        value = float(value.replace("$", "").replace(",", "").strip())
                    project_data[key] = value

            if "name" in project_data:
                projects.append(Project(**{
                    "name": project_data.get("name", ""),
                    "status": project_data.get("status", "Unknown"),
                    "start_date": project_data.get("start_date", ""),
                    "target_launch": project_data.get("target_launch", ""),
                    "budget": project_data.get("budget", 0),
                    "owner": project_data.get("owner", ""),
                    "priority": project_data.get("priority", "Medium"),
                    "description": project_data.get("description", ""),
                }))

        return projects

    def _parse_quarterly_goals(self, content: str) -> dict[str, list[str]]:
        """Parse quarterly goal sections."""
        quarterly = {}
        sections = re.findall(
            r"### (Q\d \d{4})\s*—\s*(.*?)\n((?:- \[.\].*\n)*)",
            content,
            re.MULTILINE | re.DOTALL,
        )

        for quarter, subtitle, bullets in sections:
            key = f"{quarter} — {subtitle.strip()}"
            goals_list = []
            for bullet in bullets.strip().split("\n"):
                goal = re.sub(r"- \[.\]\s*", "", bullet).strip()
                if goal:
                    goals_list.append(goal)
            quarterly[key] = goals_list

        return quarterly

    def _parse_strategic_initiatives(self, content: str) -> list[str]:
        """Parse numbered strategic initiatives."""
        initiatives = []
        matches = re.findall(r"\d+\.\s+\*\*(.*?)\*\*\s*—\s*(.*)", content)
        for title, desc in matches:
            initiatives.append(f"{title} — {desc.strip()}")
        return initiatives


# ─── Module-level convenience ─────────────────────────────────────────

_tracker = None


def get_goal_tracker() -> GoalTracker:
    """Singleton accessor."""
    global _tracker
    if _tracker is None:
        _tracker = GoalTracker()
    return _tracker


if __name__ == "__main__":
    tracker = GoalTracker()
    goals = tracker.load()

    print(f"\n🎯 Business Goals Summary")
    print("=" * 50)
    print(f"Revenue Targets: {len(goals.revenue_targets)}")
    for rt in goals.revenue_targets:
        print(f"  {rt.period}: ${rt.target:,.0f} (actual: ${rt.actual:,.0f}, {rt.progress_pct:.0f}%)")

    print(f"\nKPIs: {len(goals.kpis)}")
    for kpi in goals.kpis:
        print(f"  {kpi.status} {kpi.name}: {kpi.current} (target: {kpi.target})")

    print(f"\nProjects: {len(goals.projects)}")
    for proj in goals.projects:
        print(f"  [{proj.priority}] {proj.name} — {proj.status}")

    print(f"\nBottlenecks: {len(goals.bottlenecks)}")
    for bn in goals.bottlenecks:
        print(f"  ⚠️  {bn.description}")

    print(f"\nOverall Health: {tracker.get_overall_health()}")
    print()
