import json
import boto3
from botocore.exceptions import ClientError
from .config import Settings

TRUST = {"Version": "2012-10-17", "Statement": [{
    "Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}


def lambda_policy(bucket: str) -> dict:
    """Least-privilege: read raw/, write processed/, write own logs."""
    return {"Version": "2012-10-17", "Statement": [
        {"Sid": "ListBucketPrefixes",
         "Effect": "Allow",
         "Action": ["s3:ListBucket"],
         "Resource": f"arn:aws:s3:::{bucket}",
         "Condition": {"StringLike": {"s3:prefix": ["raw/*", "processed/*"]}}},
        {"Effect": "Allow", "Action": ["s3:GetObject"], "Resource": f"arn:aws:s3:::{bucket}/raw/*"},
        {"Effect": "Allow", "Action": ["s3:PutObject"], "Resource": f"arn:aws:s3:::{bucket}/processed/*"},
        {"Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
         "Resource": "arn:aws:logs:*:*:*"}]}


def ensure_lambda_role(s: Settings, bucket: str, client=None) -> str:
    c = client or boto3.client("iam", region_name=s.region)
    role_name = f"{s.project}-lambda-role"
    try:
        arn = c.create_role(RoleName=role_name, AssumeRolePolicyDocument=json.dumps(TRUST),
                            Tags=s.tags())["Role"]["Arn"]
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code != "EntityAlreadyExists":
            raise
        arn = c.get_role(RoleName=role_name)["Role"]["Arn"]
    c.put_role_policy(RoleName=role_name, PolicyName=f"{s.project}-s3-access",
                      PolicyDocument=json.dumps(lambda_policy(bucket)))
    return arn
