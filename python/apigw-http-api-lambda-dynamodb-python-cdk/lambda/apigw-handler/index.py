# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

# Patch all supported libraries
patch_all()

import boto3
import os
import json
import logging
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb_client = boto3.client("dynamodb")


def log_structured(level, message, **kwargs):
    """Log structured JSON for better CloudWatch Logs Insights querying"""
    log_entry = {
        "level": level,
        "message": message,
        **kwargs
    }
    logger.info(json.dumps(log_entry))


def handler(event, context):
    table = os.environ.get("TABLE_NAME")
    
    # Add annotation for tracking
    xray_recorder.put_annotation("table_name", table)
    xray_recorder.put_annotation("function_name", context.function_name)
    
    log_structured(
        "INFO",
        "Processing request",
        table_name=table,
        request_id=context.request_id,
        function_name=context.function_name
    )
    
    with xray_recorder.capture("process_request"):
        if event["body"]:
            item = json.loads(event["body"])
            
            log_structured(
                "INFO",
                "Received payload",
                payload=item,
                request_id=context.request_id
            )
            
            # Add metadata for request tracking
            xray_recorder.put_metadata("request_payload", item)
            xray_recorder.put_annotation("has_payload", True)
            
            year = str(item["year"])
            title = str(item["title"])
            id = str(item["id"])
            
            with xray_recorder.capture("dynamodb_put_item"):
                dynamodb_client.put_item(
                    TableName=table,
                    Item={"year": {"N": year}, "title": {"S": title}, "id": {"S": id}},
                )
            
            log_structured(
                "INFO",
                "Successfully inserted data",
                item_id=id,
                request_id=context.request_id
            )
            
            message = "Successfully inserted data!"
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": message}),
            }
        else:
            log_structured(
                "INFO",
                "Received request without payload, using default data",
                request_id=context.request_id
            )
            xray_recorder.put_annotation("has_payload", False)
            
            default_id = str(uuid.uuid4())
            
            with xray_recorder.capture("dynamodb_put_item"):
                dynamodb_client.put_item(
                    TableName=table,
                    Item={
                        "year": {"N": "2012"},
                        "title": {"S": "The Amazing Spider-Man 2"},
                        "id": {"S": default_id},
                    },
                )
            
            log_structured(
                "INFO",
                "Successfully inserted default data",
                item_id=default_id,
                request_id=context.request_id
            )
            
            message = "Successfully inserted data!"
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": message}),
            }
