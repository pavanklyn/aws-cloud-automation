import boto3
from .config import Settings


def ensure_bucket(s: Settings, name: str | None = None, client=None) -> str:
    """Create a private, versioned, encrypted bucket if it does not exist (idempotent)."""
    name = name or s.bucket
    c = client or boto3.client("s3", region_name=s.region)
    existing = {b["Name"] for b in c.list_buckets()["Buckets"]}
    if name not in existing:
        kwargs = {"Bucket": name}
        if s.region != "us-east-1":
            kwargs["CreateBucketConfiguration"] = {"LocationConstraint": s.region}
        c.create_bucket(**kwargs)
    c.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration={
        "BlockPublicAcls": True, "IgnorePublicAcls": True,
        "BlockPublicPolicy": True, "RestrictPublicBuckets": True})
    c.put_bucket_versioning(Bucket=name, VersioningConfiguration={"Status": "Enabled"})
    c.put_bucket_encryption(Bucket=name, ServerSideEncryptionConfiguration={
        "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]})
    return name
