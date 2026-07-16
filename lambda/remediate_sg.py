import json
import logging
import os
from datetime import datetime, timezone

import boto3


logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client("ec2")
sns = boto3.client("sns")

TARGET_SECURITY_GROUP_ID = os.environ["TARGET_SECURITY_GROUP_ID"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]

RISKY_PORT = 22
RISKY_IPV4 = "0.0.0.0/0"
RISKY_IPV6 = "::/0"


def get_items(value):
    """
    CloudTrail 이벤트 안의 items 구조를 안전하게 꺼내기 위한 함수
    """
    if not value:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, dict):
        return value.get("items", [])

    return []


def is_ssh_open_to_world(permission):
    """
    인바운드 규칙이 SSH 22번 포트를 전체 공개했는지 확인
    """
    ip_protocol = permission.get("ipProtocol")
    from_port = permission.get("fromPort")
    to_port = permission.get("toPort")

    if ip_protocol != "tcp":
        return False

    if from_port is None or to_port is None:
        return False

    if not (from_port <= RISKY_PORT <= to_port):
        return False

    ipv4_ranges = get_items(permission.get("ipRanges"))
    ipv6_ranges = get_items(permission.get("ipv6Ranges"))

    for ip_range in ipv4_ranges:
        if ip_range.get("cidrIp") == RISKY_IPV4:
            return True

    for ipv6_range in ipv6_ranges:
        if ipv6_range.get("cidrIpv6") == RISKY_IPV6:
            return True

    return False


def build_revoke_permission(permission):
    """
    위험한 규칙만 revoke_security_group_ingress 형식으로 변환
    """
    revoke_permission = {
        "IpProtocol": permission.get("ipProtocol"),
        "FromPort": permission.get("fromPort"),
        "ToPort": permission.get("toPort"),
    }

    ipv4_ranges = []
    ipv6_ranges = []

    for ip_range in get_items(permission.get("ipRanges")):
        if ip_range.get("cidrIp") == RISKY_IPV4:
            ipv4_ranges.append({
                "CidrIp": RISKY_IPV4
            })

    for ipv6_range in get_items(permission.get("ipv6Ranges")):
        if ipv6_range.get("cidrIpv6") == RISKY_IPV6:
            ipv6_ranges.append({
                "CidrIpv6": RISKY_IPV6
            })

    if ipv4_ranges:
        revoke_permission["IpRanges"] = ipv4_ranges

    if ipv6_ranges:
        revoke_permission["Ipv6Ranges"] = ipv6_ranges

    return revoke_permission


def publish_notification(message):
    """
    자동 조치 결과를 SNS Topic으로 발행
    """
    sns.publish(
        TopicArn=SNS_TOPIC_ARN,
        Subject="[Security Auto Remediation] SSH rule removed",
        Message=json.dumps(message, ensure_ascii=False, indent=2)
    )


def lambda_handler(event, context):
    logger.info("received_event=%s", json.dumps(event, ensure_ascii=False))

    detail = event.get("detail", {})
    event_name = detail.get("eventName")

    if event_name != "AuthorizeSecurityGroupIngress":
        logger.info("ignored_event eventName=%s", event_name)

        return {
            "status": "ignored",
            "reason": "event is not AuthorizeSecurityGroupIngress"
        }

    request_parameters = detail.get("requestParameters", {})
    security_group_id = request_parameters.get("groupId")

    if security_group_id != TARGET_SECURITY_GROUP_ID:
        logger.info(
            "ignored_security_group securityGroupId=%s targetSecurityGroupId=%s",
            security_group_id,
            TARGET_SECURITY_GROUP_ID
        )

        return {
            "status": "ignored",
            "reason": "security group is not remediation target",
            "securityGroupId": security_group_id
        }

    ip_permissions = get_items(request_parameters.get("ipPermissions"))
    revoke_permissions = []

    for permission in ip_permissions:
        if is_ssh_open_to_world(permission):
            revoke_permissions.append(build_revoke_permission(permission))

    if not revoke_permissions:
        logger.info(
            "no_risky_rule_found securityGroupId=%s",
            security_group_id
        )

        return {
            "status": "no_action",
            "reason": "no risky SSH rule found",
            "securityGroupId": security_group_id
        }

    ec2.revoke_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=revoke_permissions
    )

    result_message = {
        "status": "remediated",
        "securityGroupId": security_group_id,
        "removedRules": revoke_permissions,
        "eventName": event_name,
        "remediatedAt": datetime.now(timezone.utc).isoformat()
    }

    logger.warning(
        "risky_ssh_rule_removed securityGroupId=%s removedRules=%s",
        security_group_id,
        json.dumps(revoke_permissions, ensure_ascii=False)
    )

    publish_notification(result_message)

    return result_message