# Container Image Release & CD Pipeline

The Continuous Delivery workflow (`.github/workflows/release-image.yml`) runs the
repository release checks, builds and smoke-tests the BBMS Docker image, and publishes
the image with build provenance to GitHub Container Registry
(`ghcr.io/dukeavi/se_miniproject`). It delivers a versioned image; it does not
automatically deploy to a hosted production environment.

## Triggering a Release

1. Merge the intended release code to `main` and confirm its checks pass.
2. Create and push an annotated `vMAJOR.MINOR.PATCH` tag. For example:

```bash
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

The workflow rejects tags that do not contain all three numeric version parts.
It runs the release checks, builds the image, and checks `/healthz` against its
PostgreSQL service before publishing the verified image and provenance to GHCR.
The release workflow status is shown by the badge at the top of the README.

## Deploying a Release Image to a Compose host

Prepare the host using the required settings and TLS files described in
`compose.yaml`, `compose.secure.yaml`, and `.env.example`. The rollout helper
pulls the selected web, worker, Beat, and monitoring images, applies database
migrations, starts the Compose stack, waits for its services to become healthy,
and probes `/healthz` inside the web container with the configured public host
and HTTPS proxy header.

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
