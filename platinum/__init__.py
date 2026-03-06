"""
============================================================
Platinum Tier Modules
============================================================
Production-ready extensions for AI Employee system

Modules:
- health_monitor: Service health monitoring and auto-recovery
- work_zone: Work-zone specialization (Cloud vs Local)
============================================================
"""

from .health_monitor import ServiceMonitor, run_monitor
from .work_zone import (
    WorkZoneFolders,
    WorkZoneAgent,
    CloudAgent,
    LocalAgent,
    DomainType,
    get_cloud_agent,
    get_local_agent,
    initialize_work_zones,
)

__all__ = [
    # Health Monitor
    "ServiceMonitor",
    "run_monitor",
    
    # Work Zone
    "WorkZoneFolders",
    "WorkZoneAgent",
    "CloudAgent",
    "LocalAgent",
    "DomainType",
    "get_cloud_agent",
    "get_local_agent",
    "initialize_work_zones",
]

__version__ = "1.0.0"
__tier__ = "platinum"
