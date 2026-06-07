# Public Distribution Without Source Code

GitHub automatically adds source-code archives to every release created from a
tag in a repository. For Beacon, do not share releases from the source repository.

Use this split instead:

```text
beacon                 private source repo
beacon-distribution    public artifact-only repo
```

The distribution repo should contain only:

```text
README.md
LICENSE or EULA
release notes
uploaded Beacon installers/binaries
```

It should not contain the `beacon/`, `tests/`, `examples/`, or source build files
from this repository.

## Today’s Sharing Flow

1. Keep `mishraricha1806/beacon` private.
2. Run the source repo release workflow to build artifacts.
3. Download the build artifacts from GitHub Actions.
4. Create or use a separate public repository, for example:

   ```text
   mishraricha1806/beacon-distribution
   ```

5. Create a release in that distribution repo.
6. Upload only:

   ```text
   beacon-<version>-macos.pkg
   beacon-<version>-macos.pkg.sha256
   beacon-macos
   beacon-linux
   beacon-windows.exe
   ```

The distribution repo release will still show GitHub's automatic source archives,
but those archives will contain only the distribution repo contents, not Beacon's
application source code.

## Automated Distribution Release

The source repo workflow can publish artifacts directly to the distribution repo.

Create a public or private artifact-only repo, for example:

```text
mishraricha1806/beacon-distribution
```

In the private source repo, add this GitHub Actions variable:

```text
DISTRIBUTION_REPO=mishraricha1806/beacon-distribution
```

Add this GitHub Actions secret:

```text
DISTRIBUTION_REPO_TOKEN=<token with Contents: Read and write on the distribution repo>
```

Then push a new version tag from the source repo. The workflow will build Beacon
from source, download the binary artifacts inside Actions, and create/update a
release in the distribution repo.

Do not create the public release in the source repo.

## Fix If A Source Repo Release Was Already Created

Do not share that source-repo release link. Delete it or mark it internal.

Using GitHub UI:

1. Open the source repository release.
2. Delete the release.
3. Delete the tag only if you want to prevent rebuilding from that tag.
4. Re-publish the installer and binaries from the artifact-only distribution repo.

Using Git commands for the tag:

```bash
git push origin --delete v0.1.3
git tag -d v0.1.3
```

Only delete a tag if you are replacing that release.

## Distribution Repo README

Use a minimal README:

```markdown
# Beacon

Production-readiness intelligence for distributed systems.

Download the latest installer or binary from Releases.

## macOS

sudo installer -pkg beacon-<version>-macos.pkg -target /
beacon --help

## Linux

chmod +x beacon-linux
./beacon-linux --help

## Windows

beacon-windows.exe --help
```
