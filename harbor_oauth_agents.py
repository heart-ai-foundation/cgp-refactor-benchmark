"""Harbor agent wrappers that bridge local CLI OAuth credentials into tasks."""

from __future__ import annotations

import json
import os
import shlex
from pathlib import Path
from typing import Any

from harbor.agents.installed.claude_code import ClaudeCode
from harbor.agents.installed.gemini_cli import GeminiCli
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext
from harbor.models.trial.paths import EnvironmentPaths


def _host_path(env_name: str, default: Path) -> Path | None:
    raw = os.environ.get(env_name)
    path = Path(raw).expanduser() if raw else default
    return path if path.exists() else None


class ClaudeCodeOAuth(ClaudeCode):
    """Claude Code agent that copies the local Linux OAuth credential file."""

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        credentials = _host_path(
            "CLAUDE_CODE_CREDENTIALS_PATH",
            Path.home() / ".claude" / ".credentials.json",
        )
        if credentials:
            remote_config_dir = EnvironmentPaths.agent_dir / "sessions"
            remote_credentials = remote_config_dir / ".credentials.json"
            await self.exec_as_agent(
                environment,
                command=f"mkdir -p {shlex.quote(remote_config_dir.as_posix())}",
            )
            await environment.upload_file(credentials, remote_credentials.as_posix())
            if environment.default_user is not None:
                await self.exec_as_root(
                    environment,
                    command=(
                        f"chown {environment.default_user} "
                        f"{shlex.quote(remote_credentials.as_posix())}"
                    ),
                )
            await self.exec_as_agent(
                environment,
                command=f"chmod 600 {shlex.quote(remote_credentials.as_posix())}",
            )
        return await super().run(instruction, environment, context)


class GeminiCliOAuth(GeminiCli):
    """Gemini CLI agent that copies local OAuth credentials and auth settings."""

    def _build_settings_config(
        self, model: str | None = None
    ) -> tuple[dict[str, Any] | None, str | None]:
        config, model_alias = super()._build_settings_config(model)
        config = dict(config or {})
        security = dict(config.get("security") or {})
        auth = dict(security.get("auth") or {})
        auth.setdefault("selectedType", os.environ.get("GEMINI_AUTH_TYPE", "oauth-personal"))
        security["auth"] = auth
        config["security"] = security
        config.setdefault("experimental", {"skills": True})
        return config, model_alias

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        gemini_home = Path.home() / ".gemini"
        files = [
            (
                _host_path("GEMINI_OAUTH_CREDS_PATH", gemini_home / "oauth_creds.json"),
                "oauth_creds.json",
                "600",
            ),
            (
                _host_path("GEMINI_GOOGLE_ACCOUNTS_PATH", gemini_home / "google_accounts.json"),
                "google_accounts.json",
                "600",
            ),
        ]
        await self.exec_as_agent(environment, command="mkdir -p ~/.gemini")
        for source, filename, mode in files:
            if source is None:
                continue
            remote_tmp = f"/tmp/harbor-{filename}"
            await environment.upload_file(source, remote_tmp)
            await self.exec_as_agent(
                environment,
                command=(
                    f"cp {shlex.quote(remote_tmp)} ~/.gemini/{shlex.quote(filename)} "
                    f"&& chmod {mode} ~/.gemini/{shlex.quote(filename)}"
                ),
            )
        return await super().run(instruction, environment, context)
