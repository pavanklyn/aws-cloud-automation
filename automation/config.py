import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    region: str = os.getenv("AWS_REGION", "ap-south-1")
    project: str = os.getenv("PROJECT_NAME", "cloud-automation")
    bucket: str = os.getenv("BUCKET_NAME", "")
    instance_type: str = os.getenv("INSTANCE_TYPE", "t3.micro")
    ami_id: str = os.getenv("AMI_ID", "")
    alarm_topic_arn: str = os.getenv("ALARM_TOPIC_ARN", "")

    def tags(self):
        return [{"Key": "Project", "Value": self.project}, {"Key": "ManagedBy", "Value": "automation"}]
