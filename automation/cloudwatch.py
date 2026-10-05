import boto3
from .config import Settings


def _actions(s: Settings):
    return [s.alarm_topic_arn] if s.alarm_topic_arn else []


def create_ec2_cpu_alarm(s: Settings, instance_id: str, threshold: float = 80.0, client=None) -> str:
    c = client or boto3.client("cloudwatch", region_name=s.region)
    name = f"{s.project}-{instance_id}-high-cpu"
    c.put_metric_alarm(AlarmName=name, Namespace="AWS/EC2", MetricName="CPUUtilization",
                       Dimensions=[{"Name": "InstanceId", "Value": instance_id}], Statistic="Average",
                       Period=300, EvaluationPeriods=2, Threshold=threshold,
                       ComparisonOperator="GreaterThanThreshold", AlarmActions=_actions(s))
    return name


def create_lambda_error_alarm(s: Settings, function_name: str, client=None) -> str:
    c = client or boto3.client("cloudwatch", region_name=s.region)
    name = f"{s.project}-{function_name}-errors"
    c.put_metric_alarm(AlarmName=name, Namespace="AWS/Lambda", MetricName="Errors",
                       Dimensions=[{"Name": "FunctionName", "Value": function_name}], Statistic="Sum",
                       Period=60, EvaluationPeriods=1, Threshold=0,
                       ComparisonOperator="GreaterThanThreshold", TreatMissingData="notBreaching",
                       AlarmActions=_actions(s))
    return name
