# Container Image Release & CD Pipeline

The Continuous Delivery workflow (`.github/workflows/release-image.yml`) runs the
repository release checks, builds and smoke-tests the BBMS Docker image, and publishes
the image with build provenance to GitHub Container Registry
(`ghcr.io/dukeavi/se_miniproject`). It delivers a versioned image; it does not
automatically deploy to a hosted production environment.

## Triggering a Release

1. Ensure `main` is green and all issue checks pass.
2. Create and push an annotated semantic version tag matching `v*`:

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

## Deploying a Release Image to a Compose host

Authenticate on the target host using a token with `read:packages` scope:

```bash
echo "$GHCR_TOKEN" | docker login ghcr.io -u <github-username> --password-stdin
```

Execute the rollout helper with the target release tag:

```bash
./deployment/rollout.sh v1.0.0
```

## Rollback Procedure

If post-deploy checks or `/healthz` probes fail, redeploy the previous known-good version tag:

```bash
./deployment/rollout.sh v0.9.0
```
