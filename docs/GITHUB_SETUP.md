# GitHub Setup For Private Source Releases

Beacon's recommended release model is:

```text
private source repo -> build artifacts -> public artifact-only distribution repo
```

Users receive installers and standalone binaries. They do not need source
repository access.

## Repository

1. Keep the GitHub repository private.
2. Protect `main`.
3. Require release checks before merging release changes.

## Required Workflow

The release workflow lives at:

```text
.github/workflows/release.yml
```

It runs release checks, builds platform binaries, builds the macOS `.pkg`, and
uploads binary/installer artifacts to the workflow run.

Do not share releases from the source repository. GitHub automatically attaches
source-code archives to tag-based releases.

No PyPI token is required for the private-source release path.

## Distribution Repo Automation

Create a separate artifact-only repo, for example:

```text
mishraricha1806/beacon-distribution
```

In the private source repo, configure:

```text
Actions variable:
DISTRIBUTION_REPO=mishraricha1806/beacon-distribution

Actions secret:
DISTRIBUTION_REPO_TOKEN=<token with Contents: Read and write on the distribution repo>
```

When a version tag is pushed, the workflow builds artifacts from the source repo
and publishes the shareable release to the distribution repo.

## Local Release Check

Run before tagging:

```bash
python3 scripts/release_check_all.py --require-helm
```

## Local Artifact Build

```bash
./scripts/package.sh all
```

On macOS, this also creates:

```text
dist-binaries/beacon-<version>-macos.pkg
```

## Create A Release Tag

```bash
git tag -a v0.1.2 -m "Release v0.1.2"
git push origin v0.1.2
```

## Verify Build Artifacts

The workflow artifacts should include:

```text
beacon-<version>-macos.pkg
beacon-<version>-macos.pkg.sha256
beacon-macos
beacon-linux
beacon-windows.exe
```

Publish those files from a separate artifact-only distribution repository. See
[PUBLIC_DISTRIBUTION.md](PUBLIC_DISTRIBUTION.md).

## User Install Paths

macOS:

```bash
sudo installer -pkg beacon-<version>-macos.pkg -target /
beacon --help
```

Linux:

```bash
chmod +x beacon-linux
./beacon-linux --help
```

Windows:

```powershell
beacon-windows.exe --help
```
