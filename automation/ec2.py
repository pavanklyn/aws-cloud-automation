import boto3
from .config import Settings


def launch_instance(s: Settings, client=None) -> str:
    if not s.ami_id:
        raise ValueError("AMI_ID is required")
    c = client or boto3.client("ec2", region_name=s.region)
    res = c.run_instances(
        ImageId=s.ami_id, InstanceType=s.instance_type, MinCount=1, MaxCount=1,
        Monitoring={"Enabled": True},
        MetadataOptions={"HttpTokens": "required"},  # enforce IMDSv2
        TagSpecifications=[{"ResourceType": "instance", "Tags": s.tags()}])
    return res["Instances"][0]["InstanceId"]


def list_project_instances(s: Settings, client=None) -> list[dict]:
    c = client or boto3.client("ec2", region_name=s.region)
    pages = c.get_paginator("describe_instances").paginate(
        Filters=[{"Name": "tag:Project", "Values": [s.project]},
                 {"Name": "instance-state-name", "Values": ["pending", "running", "stopped"]}])
    return [{"id": i["InstanceId"], "state": i["State"]["Name"]}
            for p in pages for r in p["Reservations"] for i in r["Instances"]]


def stop_project_instances(s: Settings, client=None) -> list[str]:
    c = client or boto3.client("ec2", region_name=s.region)
    ids = [i["id"] for i in list_project_instances(s, c) if i["state"] == "running"]
    if ids:
        c.stop_instances(InstanceIds=ids)
    return ids
