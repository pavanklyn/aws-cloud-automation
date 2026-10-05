import argparse
import json

from .config import Settings
from . import cloudwatch, ec2, iam, lambda_deploy, s3


def main(argv=None):
    p = argparse.ArgumentParser(prog="automation", description="AWS provisioning automation")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("provision-pipeline", help="bucket + IAM role + Lambda + S3 trigger + alarm")
    sub.add_parser("launch-ec2", help="launch tagged instance with CPU alarm")
    sub.add_parser("list-ec2")
    sub.add_parser("stop-ec2", help="stop all running project instances")
    a = p.parse_args(argv)
    cfg = Settings()

    if a.cmd == "provision-pipeline":
        bucket = s3.ensure_bucket(cfg)
        role = iam.ensure_lambda_role(cfg, bucket)
        fn = lambda_deploy.deploy_s3_pipeline(cfg, role, bucket)
        alarm = cloudwatch.create_lambda_error_alarm(cfg, fn)
        out = {"bucket": bucket, "role": role, "function": fn, "alarm": alarm}
    elif a.cmd == "launch-ec2":
        iid = ec2.launch_instance(cfg)
        out = {"instance": iid, "alarm": cloudwatch.create_ec2_cpu_alarm(cfg, iid)}
    elif a.cmd == "list-ec2":
        out = ec2.list_project_instances(cfg)
    else:
        out = {"stopped": ec2.stop_project_instances(cfg)}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
