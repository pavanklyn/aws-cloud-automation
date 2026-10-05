import io
import zipfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError
from .config import Settings

HANDLER_DIR = Path(__file__).resolve().parent.parent / "lambda_functions" / "s3_processor"


def build_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(HANDLER_DIR / "handler.py", "handler.py")
    return buf.getvalue()


def deploy_s3_pipeline(s: Settings, role_arn: str, bucket: str, lam=None, s3=None) -> str:
    """Create/update the processor Lambda and wire S3 raw/ uploads to trigger it."""
    lam = lam or boto3.client("lambda", region_name=s.region)
    s3 = s3 or boto3.client("s3", region_name=s.region)
    fn = f"{s.project}-s3-processor"
    code = build_zip()
    env = {"Variables": {"OUTPUT_PREFIX": "processed/"}}
    try:
        arn = lam.create_function(FunctionName=fn, Runtime="python3.12", Role=role_arn, Handler="handler.lambda_handler",
                                  Code={"ZipFile": code}, Timeout=30, Environment=env, Tags={"Project": s.project})["FunctionArn"]
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceConflictException":
            raise
        lam.update_function_code(FunctionName=fn, ZipFile=code)
        arn = lam.get_function(FunctionName=fn)["Configuration"]["FunctionArn"]
    try:
        lam.add_permission(FunctionName=fn, StatementId="s3-invoke", Action="lambda:InvokeFunction",
                           Principal="s3.amazonaws.com", SourceArn=f"arn:aws:s3:::{bucket}")
    except ClientError as e:
        if e.response["Error"]["Code"] != "ResourceConflictException":
            raise
    s3.put_bucket_notification_configuration(Bucket=bucket, NotificationConfiguration={
        "LambdaFunctionConfigurations": [{"LambdaFunctionArn": arn, "Events": ["s3:ObjectCreated:*"],
                                          "Filter": {"Key": {"FilterRules": [{"Name": "prefix", "Value": "raw/"}]}}}]})
    return fn
