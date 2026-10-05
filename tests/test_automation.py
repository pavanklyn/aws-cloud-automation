import json

import boto3
import pytest
from moto import mock_aws

from automation import cloudwatch, ec2, iam, lambda_deploy, s3 as s3mod
from automation.config import Settings
from lambda_functions.s3_processor import handler

REGION = "ap-south-1"
CFG = Settings(region=REGION, project="demo", bucket="demo-bucket-123", ami_id="ami-12345678")


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SECURITY_TOKEN", "AWS_SESSION_TOKEN"):
        monkeypatch.setenv(k, "testing")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


@mock_aws
def test_bucket_is_secured_and_idempotent():
    c = boto3.client("s3", region_name=REGION)
    s3mod.ensure_bucket(CFG, client=c)
    s3mod.ensure_bucket(CFG, client=c)  # second run must not fail
    assert c.get_bucket_versioning(Bucket=CFG.bucket)["Status"] == "Enabled"
    assert c.get_public_access_block(Bucket=CFG.bucket)["PublicAccessBlockConfiguration"]["BlockPublicAcls"]


@mock_aws
def test_iam_role_idempotent_and_least_privilege():
    c = boto3.client("iam")
    a1 = iam.ensure_lambda_role(CFG, CFG.bucket, client=c)
    a2 = iam.ensure_lambda_role(CFG, CFG.bucket, client=c)
    assert a1 == a2
    pol = c.get_role_policy(RoleName="demo-lambda-role", PolicyName="demo-s3-access")["PolicyDocument"]
    assert all("*" != st["Resource"] for st in pol["Statement"])


@mock_aws
def test_ec2_launch_list_stop_and_alarm():
    c = boto3.client("ec2", region_name=REGION)
    ami = c.describe_images()["Images"][0]["ImageId"]
    cfg = Settings(region=REGION, project="demo", ami_id=ami)
    iid = ec2.launch_instance(cfg, client=c)
    assert [i["id"] for i in ec2.list_project_instances(cfg, client=c)] == [iid]
    assert ec2.stop_project_instances(cfg, client=c) == [iid]
    cw = boto3.client("cloudwatch", region_name=REGION)
    name = cloudwatch.create_ec2_cpu_alarm(cfg, iid, client=cw)
    assert cw.describe_alarms(AlarmNames=[name])["MetricAlarms"][0]["Threshold"] == 80.0


def test_launch_requires_ami():
    with pytest.raises(ValueError):
        ec2.launch_instance(Settings(ami_id=""))


@mock_aws
def test_lambda_pipeline_deploys_and_is_idempotent():
    s3c = boto3.client("s3", region_name=REGION)
    lam = boto3.client("lambda", region_name=REGION)
    s3mod.ensure_bucket(CFG, client=s3c)
    role = iam.ensure_lambda_role(CFG, CFG.bucket)
    fn = lambda_deploy.deploy_s3_pipeline(CFG, role, CFG.bucket, lam=lam, s3=s3c)
    fn2 = lambda_deploy.deploy_s3_pipeline(CFG, role, CFG.bucket, lam=lam, s3=s3c)
    assert fn == fn2 == "demo-s3-processor"
    cfgs = s3c.get_bucket_notification_configuration(Bucket=CFG.bucket)["LambdaFunctionConfigurations"]
    assert cfgs[0]["Filter"]["Key"]["FilterRules"][0]["Value"] == "raw/"
    cw = boto3.client("cloudwatch", region_name=REGION)
    assert cloudwatch.create_lambda_error_alarm(CFG, fn, client=cw)


@mock_aws
def test_handler_writes_summary(monkeypatch):
    c = boto3.client("s3", region_name=REGION)
    c.create_bucket(Bucket="test-bucket", CreateBucketConfiguration={"LocationConstraint": REGION})
    c.put_object(Bucket="test-bucket", Key="raw/data.txt", Body=b"a,b\n1,2\n3,4\n")
    monkeypatch.setattr(handler, "s3", c)
    event = {"Records": [{"s3": {"bucket": {"name": "test-bucket"}, "object": {"key": "raw/data.txt"}}}]}
    assert handler.lambda_handler(event)["processed"] == ["processed/data.txt.summary.json"]
    out = json.loads(c.get_object(Bucket="test-bucket", Key="processed/data.txt.summary.json")["Body"].read())
    assert out["line_count"] == 3


@mock_aws
def test_handler_skips_own_output(monkeypatch):
    c = boto3.client("s3", region_name=REGION)
    monkeypatch.setattr(handler, "s3", c)
    event = {"Records": [{"s3": {"bucket": {"name": "test-bucket"}, "object": {"key": "processed/x.json"}}}]}
    assert handler.lambda_handler(event) == {"processed": []}
