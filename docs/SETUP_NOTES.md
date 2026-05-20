# Setup Notes

## Harbor

Installed locally with:

```bash
uv tool install harbor
```

Installed version observed:

- `harbor==0.7.1`
- executables: `harbor`, `hb`, `hr`

## Container Runtime

Harbor's Docker environment checks for a `docker` executable and uses
`docker compose`. Use real Docker rather than a Podman compatibility shim for
benchmark runs.

Observed working local setup on Fedora 44:

```bash
sudo dnf --disablerepo='tailscale-stable' \
  --disablerepo='copr:copr.fedorainfracloud.org:pgdev:ghostty' \
  install -y moby-engine docker-cli docker-compose
dockerd-rootless-setuptool.sh install
docker context use rootless
```

Installed Docker versions observed:

- Docker CLI/Engine `29.4.2`
- Docker Compose `5.1.2`
- Rootless Docker socket `/run/user/1000/docker.sock`

The old local Podman shim was moved aside to:

```bash
/home/dylan/.local/bin/docker.podman-shim.bak
```

Smoke validation after switching to real Docker:

```bash
harbor run \
  --path /home/dylan/cgp-refactor-benchmark/tasks/harbor/codescalebench-refactor \
  --agent nop \
  --n-concurrent 1 \
  --n-tasks 1 \
  --jobs-dir /home/dylan/cgp-refactor-benchmark/runs/harbor-smoke \
  --yes
```

Expected smoke result for the NOP agent is a completed trial with no
infrastructure exception and reward `0.0`.
