# Database Schema

## Current state

CodeScope v2 has no database and no persistent service. Analysis exists only for the duration of a GitHub Actions run. The durable outputs are GitHub workflow logs, the stable pull-request comment, repository policy, and Git history.

## Data ownership

GitHub controls retention for workflow logs and comments under the repository owner's settings and agreement. CodeScope does not create accounts or store a separate copy.

## Future schema

A future hosted service might store repository installations, graph snapshots, finding feedback, suppressions, or historical outcomes. That work is outside the v2 scope. Before adding storage, define retention, deletion, access control, tenancy isolation, regional processing, backup, encryption, and data-subject request behavior. All fields remain `TBD` until a hosted-service decision is approved.
