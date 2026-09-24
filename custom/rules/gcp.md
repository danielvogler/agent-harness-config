# GCP — conventions

## What data may go into the cloud at all

Whoever puts data somewhere is the one who classifies it. Four levels: **public**,
**internal**, **confidential**, **strictly confidential**.

- **Public and internal** — fine in a project bucket.
- **Confidential** — needs a cloud assessment first. Ask before uploading.
- **Strictly confidential** — never goes to an external cloud service at all.

Unsure which level? Then it is not public. Ask before uploading.

## Credentials

- **Application Default Credentials** for people, attached service accounts for workloads.
- **Never create or download a service-account key file.** A `*.json` key in a repo, a
  home directory or an image is the most common way a project like this leaks. One that
  already exists is compromised: rotate, then delete.
- Secrets live in **Secret Manager**, fetched at runtime — never a committed `.env`, an
  infrastructure variable, or a notebook cell.
- Never print or log a credential, token, or full signed URL.

## Always name the project

Read the project from the active gcloud configuration (`gcloud config get project`), say
which one you are using, and still pass `--project` explicitly on every command. An unstated
ambient default is why things get run against the wrong project.

## Destructive operations need a yes first

`gcloud ... delete`, `bq rm`, `gsutil rm -r`, `terraform destroy` / `tofu destroy`, and
anything dropping a dataset, bucket, table or project: **say what will be destroyed and
wait for explicit confirmation in the conversation.** Do not infer approval from an earlier
unrelated yes. Prefer a reversible step — disable, detach, lifecycle-expire — when one
exists.

## Regions

Pin the region rather than accepting a provider default. Read it from the active gcloud
configuration (`gcloud config get compute/region`); if it is empty, ask the user. Never leave
a bucket, dataset or job in `US` by accident.
Where a data-residency requirement applies, it decides; check before assuming it does not.

## BigQuery — cost is the failure mode, not correctness

- **Dry-run anything unfamiliar** and read the byte estimate first.
- **Set `maximum_bytes_billed` on every programmatic query.** That is what turns a runaway
  query into an error instead of an invoice.
- **Filter the partition column**, and never `SELECT *` on a partitioned or wide table.
