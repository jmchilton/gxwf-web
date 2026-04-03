"""Git-backed project management: clone, checkout, discover workflows."""

import os
import tempfile
from typing import (
    Dict,
    List,
    Optional,
)

from git import Repo

from galaxy.tool_util.workflow_state.workflow_tree import (
    discover_workflows,
    WorkflowInfo,
)

from .models import (
    ProjectConfig,
    WorkflowEntry,
    WorkflowIndex,
)


class Project:
    """A cloned GitHub project with discovered workflows."""

    def __init__(self, config: ProjectConfig, clone_root: Optional[str] = None):
        self.config = config
        self._clone_root = clone_root or os.path.join(tempfile.gettempdir(), "gxwf-projects")
        self._repo: Optional[Repo] = None
        self._workflows: Optional[List[WorkflowInfo]] = None

    @property
    def slug(self) -> str:
        return f"{self.config.owner}/{self.config.repo}"

    @property
    def local_path(self) -> str:
        if self.config.local_path:
            return self.config.local_path
        return os.path.join(self._clone_root, self.config.owner, self.config.repo)

    def ensure_cloned(self) -> str:
        path = self.local_path
        if os.path.isdir(os.path.join(path, ".git")):
            self._repo = Repo(path)
            self._fetch_and_checkout()
        elif self.config.local_path:
            raise FileNotFoundError(f"Local path {path} does not exist")
        else:
            url = f"https://github.com/{self.slug}.git"
            self._repo = Repo.clone_from(url, path, no_checkout=True)
            self._fetch_and_checkout()
        self._workflows = None
        return path

    def _fetch_and_checkout(self):
        assert self._repo is not None
        self._repo.remotes.origin.fetch()
        self._repo.git.checkout(self.config.ref)

    def discover(self) -> List[WorkflowInfo]:
        if self._workflows is None:
            self._workflows = discover_workflows(self.local_path)
        return self._workflows

    def get_workflow(self, relative_path: str) -> Optional[WorkflowInfo]:
        for wf in self.discover():
            if wf.relative_path == relative_path:
                return wf
        return None

    def index(self) -> WorkflowIndex:
        return WorkflowIndex(
            project=self.slug,
            ref=self.config.ref,
            workflows=[
                WorkflowEntry(
                    relative_path=wf.relative_path,
                    format=wf.format,
                    category=wf.category,
                )
                for wf in self.discover()
            ],
        )


class ProjectRegistry:
    """In-memory registry of configured projects."""

    def __init__(self, clone_root: Optional[str] = None):
        self._projects: Dict[str, Project] = {}
        self._clone_root = clone_root

    def add(self, config: ProjectConfig) -> Project:
        project = Project(config, clone_root=self._clone_root)
        self._projects[project.slug] = project
        return project

    def get(self, owner: str, repo: str) -> Optional[Project]:
        return self._projects.get(f"{owner}/{repo}")

    def list_projects(self) -> List[Project]:
        return list(self._projects.values())
