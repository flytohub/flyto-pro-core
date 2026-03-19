"""
Flyto Directory - .flyto/ directory structure management.

Standard structure:
.flyto/
  state.json          # Current project state
  config.json         # Project configuration
  goals/              # Goal history
    {goal_id}.json
  artifacts/          # Step artifacts
    {step_id}/
      screenshot.png
      output.json
  ems/                # Error Memory System
    patterns.json
    pending/
  logs/               # Execution logs
    {session_id}.log
  bundles/            # Execution bundles for replay
    {bundle_id}.json
"""

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DirectoryStructure:
    """Defines the .flyto directory structure."""

    # Root paths
    STATE_FILE = "state.json"
    CONFIG_FILE = "config.json"

    # Subdirectories
    GOALS_DIR = "goals"
    ARTIFACTS_DIR = "artifacts"
    EMS_DIR = "ems"
    LOGS_DIR = "logs"
    BUNDLES_DIR = "bundles"
    CACHE_DIR = "cache"

    # EMS subdirectories
    EMS_PATTERNS_FILE = "ems/patterns.json"
    EMS_PENDING_DIR = "ems/pending"
    EMS_ACTIVE_DIR = "ems/active"

    @classmethod
    def get_all_dirs(cls) -> List[str]:
        """Get all directory names."""
        return [
            cls.GOALS_DIR,
            cls.ARTIFACTS_DIR,
            cls.EMS_DIR,
            cls.LOGS_DIR,
            cls.BUNDLES_DIR,
            cls.CACHE_DIR,
            cls.EMS_PENDING_DIR,
            cls.EMS_ACTIVE_DIR,
        ]


class FlytoDirectory:
    """
    Manages the .flyto/ directory structure.

    Handles creation, validation, and cleanup.
    """

    def __init__(self, project_path: str):
        self.project_path = project_path
        self.flyto_path = os.path.join(project_path, ".flyto")

    @property
    def exists(self) -> bool:
        """Check if .flyto directory exists."""
        return os.path.exists(self.flyto_path)

    def initialize(self) -> bool:
        """Create .flyto directory structure."""
        try:
            # Create root
            os.makedirs(self.flyto_path, exist_ok=True)

            # Create subdirectories
            for dir_name in DirectoryStructure.get_all_dirs():
                dir_path = os.path.join(self.flyto_path, dir_name)
                os.makedirs(dir_path, exist_ok=True)

            # Create .gitignore
            gitignore_path = os.path.join(self.flyto_path, ".gitignore")
            if not os.path.exists(gitignore_path):
                with open(gitignore_path, "w") as f:
                    f.write("# Flyto local files\n")
                    f.write("cache/\n")
                    f.write("logs/\n")
                    f.write("*.log\n")
                    f.write("# Keep artifacts and state\n")
                    f.write("!artifacts/\n")
                    f.write("!state.json\n")

            logger.info(f"Initialized .flyto directory at {self.flyto_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize .flyto: {e}")
            return False

    def validate(self) -> Dict[str, bool]:
        """Validate directory structure."""
        results = {"root": os.path.exists(self.flyto_path)}

        for dir_name in DirectoryStructure.get_all_dirs():
            dir_path = os.path.join(self.flyto_path, dir_name)
            results[dir_name] = os.path.exists(dir_path)

        return results

    def repair(self) -> bool:
        """Repair missing directories."""
        if not self.exists:
            return self.initialize()

        try:
            for dir_name in DirectoryStructure.get_all_dirs():
                dir_path = os.path.join(self.flyto_path, dir_name)
                os.makedirs(dir_path, exist_ok=True)

            logger.info("Repaired .flyto directory structure")
            return True

        except Exception as e:
            logger.error(f"Failed to repair .flyto: {e}")
            return False

    # Path helpers
    def get_state_path(self) -> str:
        """Get state.json path."""
        return os.path.join(self.flyto_path, DirectoryStructure.STATE_FILE)

    def get_config_path(self) -> str:
        """Get config.json path."""
        return os.path.join(self.flyto_path, DirectoryStructure.CONFIG_FILE)

    def get_goal_path(self, goal_id: str) -> str:
        """Get goal file path."""
        return os.path.join(
            self.flyto_path, DirectoryStructure.GOALS_DIR, f"{goal_id}.json"
        )

    def get_artifact_dir(self, step_id: str) -> str:
        """Get artifact directory for step."""
        path = os.path.join(
            self.flyto_path, DirectoryStructure.ARTIFACTS_DIR, step_id
        )
        os.makedirs(path, exist_ok=True)
        return path

    def get_log_path(self, session_id: str) -> str:
        """Get log file path for session."""
        return os.path.join(
            self.flyto_path, DirectoryStructure.LOGS_DIR, f"{session_id}.log"
        )

    def get_bundle_path(self, bundle_id: str) -> str:
        """Get execution bundle path."""
        return os.path.join(
            self.flyto_path, DirectoryStructure.BUNDLES_DIR, f"{bundle_id}.json"
        )

    def get_ems_patterns_path(self) -> str:
        """Get EMS patterns file path."""
        return os.path.join(self.flyto_path, DirectoryStructure.EMS_PATTERNS_FILE)

    def get_ems_pending_path(self, pattern_id: str) -> str:
        """Get pending EMS pattern path."""
        return os.path.join(
            self.flyto_path, DirectoryStructure.EMS_PENDING_DIR, f"{pattern_id}.json"
        )

    def get_ems_active_path(self, pattern_id: str) -> str:
        """Get active EMS pattern path."""
        return os.path.join(
            self.flyto_path, DirectoryStructure.EMS_ACTIVE_DIR, f"{pattern_id}.json"
        )

    # Artifact management
    def save_artifact(
        self,
        step_id: str,
        artifact_name: str,
        data: Any,
        is_binary: bool = False,
    ) -> str:
        """Save artifact and return path."""
        artifact_dir = self.get_artifact_dir(step_id)
        artifact_path = os.path.join(artifact_dir, artifact_name)

        if is_binary:
            with open(artifact_path, "wb") as f:
                f.write(data)
        else:
            if isinstance(data, (dict, list)):
                with open(artifact_path, "w") as f:
                    json.dump(data, f, indent=2)
            else:
                with open(artifact_path, "w") as f:
                    f.write(str(data))

        return artifact_path

    def load_artifact(
        self,
        step_id: str,
        artifact_name: str,
        is_binary: bool = False,
    ) -> Optional[Any]:
        """Load artifact."""
        artifact_path = os.path.join(
            self.flyto_path, DirectoryStructure.ARTIFACTS_DIR, step_id, artifact_name
        )

        if not os.path.exists(artifact_path):
            return None

        try:
            if is_binary:
                with open(artifact_path, "rb") as f:
                    return f.read()
            else:
                with open(artifact_path, "r") as f:
                    content = f.read()
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        return content
        except Exception as e:
            logger.error(f"Failed to load artifact: {e}")
            return None

    def list_artifacts(self, step_id: str) -> List[str]:
        """List artifacts for step."""
        artifact_dir = os.path.join(
            self.flyto_path, DirectoryStructure.ARTIFACTS_DIR, step_id
        )

        if not os.path.exists(artifact_dir):
            return []

        return os.listdir(artifact_dir)

    # Cleanup
    def cleanup_cache(self) -> int:
        """Clean up cache directory."""
        cache_dir = os.path.join(self.flyto_path, DirectoryStructure.CACHE_DIR)
        if not os.path.exists(cache_dir):
            return 0

        count = 0
        for f in os.listdir(cache_dir):
            try:
                path = os.path.join(cache_dir, f)
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to remove cache item: {e}")

        return count

    def cleanup_old_logs(self, keep_days: int = 7) -> int:
        """Clean up old log files."""
        logs_dir = os.path.join(self.flyto_path, DirectoryStructure.LOGS_DIR)
        if not os.path.exists(logs_dir):
            return 0

        cutoff = datetime.utcnow().timestamp() - (keep_days * 86400)
        count = 0

        for f in os.listdir(logs_dir):
            path = os.path.join(logs_dir, f)
            if os.path.isfile(path):
                if os.path.getmtime(path) < cutoff:
                    try:
                        os.remove(path)
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove old log: {e}")

        return count

    def cleanup_old_artifacts(self, keep_days: int = 30) -> int:
        """Clean up old artifact directories."""
        artifacts_dir = os.path.join(self.flyto_path, DirectoryStructure.ARTIFACTS_DIR)
        if not os.path.exists(artifacts_dir):
            return 0

        cutoff = datetime.utcnow().timestamp() - (keep_days * 86400)
        count = 0

        for d in os.listdir(artifacts_dir):
            path = os.path.join(artifacts_dir, d)
            if os.path.isdir(path):
                if os.path.getmtime(path) < cutoff:
                    try:
                        shutil.rmtree(path)
                        count += 1
                    except Exception as e:
                        logger.warning(f"Failed to remove old artifact: {e}")

        return count

    def get_size_stats(self) -> Dict[str, int]:
        """Get directory size statistics."""
        stats = {}

        for dir_name in DirectoryStructure.get_all_dirs():
            dir_path = os.path.join(self.flyto_path, dir_name)
            if os.path.exists(dir_path):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(dir_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)
                stats[dir_name] = total_size
            else:
                stats[dir_name] = 0

        return stats


# Factory function
def get_flyto_directory(project_path: str) -> FlytoDirectory:
    """Get FlytoDirectory for project path."""
    return FlytoDirectory(project_path)
