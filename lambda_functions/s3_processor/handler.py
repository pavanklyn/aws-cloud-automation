"""S3-triggered Lambda: reads a JSON-lines/CSV-ish upload under raw/, writes a summary under processed/."""
import json
import os
import urllib.parse

import boto3

s3 = boto3.client("s3")


def summarize(body: str) -> dict:
    lines = [l for l in body.splitlines() if l.strip()]
    return {"line_count": len(lines), "char_count": len(body), "first_line": lines[0] if lines else ""}


def lambda_handler(event, context=None):
    out_prefix = os.getenv("OUTPUT_PREFIX", "processed/")
    results = []
    for rec in event.get("Records", []):
        bucket = rec["s3"]["bucket"]["name"]
        key = urllib.parse.unquote_plus(rec["s3"]["object"]["key"])
        if key.startswith(out_prefix):  # never reprocess our own output
            continue
        body = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8", errors="replace")
        out_key = out_prefix + key.split("/", 1)[-1] + ".summary.json"
        s3.put_object(Bucket=bucket, Key=out_key, Body=json.dumps(summarize(body)).encode(),
                      ContentType="application/json")
        results.append(out_key)
    return {"processed": results}
