"""Unit tests for CloudFormation custom / Serverless macro detection."""

from ministack.services.cloudformation.custom_syntax import (
    scan_template_for_custom_placeholders,
    warn_or_reject_custom_syntax,
)


def test_scan_detects_file_placeholder():
    t = {
        "Resources": {
            "R": {
                "Type": "AWS::Lambda::Function",
                "Properties": {"Code": {"ZipFile": "${file(../foo.js)}"}},
            },
        },
    }
    hits = scan_template_for_custom_placeholders(t)
    assert any("${file(" in h for h in hits)


def test_scan_detects_self_placeholder():
    t = {"Resources": {"Q": {"Properties": {"QueueName": "${self:service}-${self:provider.stage}"}}}}
    hits = scan_template_for_custom_placeholders(t)
    assert any("${self:" in h for h in hits)


def test_scan_detects_mason_fn_type():
    t = {"Resources": {"X": {"Type": "MasonFn::HyperionFamilyGet", "Properties": {}}}}
    hits = scan_template_for_custom_placeholders(t)
    assert any("MasonFn::" in h for h in hits)


def test_scan_clean_template():
    t = {
        "Resources": {
            "B": {"Type": "AWS::S3::Bucket", "Properties": {"BucketName": "plain-name"}},
        },
    }
    assert scan_template_for_custom_placeholders(t) == []


def test_warn_or_reject_strict_mode(monkeypatch):
    t = {"Resources": {"B": {"Type": "AWS::S3::Bucket", "Properties": {"BucketName": "${file(x)}"}}}}
    monkeypatch.delenv("MINISTACK_CFN_FAIL_ON_CUSTOM_SYNTAX", raising=False)
    assert warn_or_reject_custom_syntax(t) is None

    monkeypatch.setenv("MINISTACK_CFN_FAIL_ON_CUSTOM_SYNTAX", "1")
    msg = warn_or_reject_custom_syntax(t)
    assert msg is not None
    assert "does not evaluate" in msg
    assert "MINISTACK_CFN_FAIL_ON_CUSTOM_SYNTAX" in msg


def test_warn_or_reject_respects_off_values(monkeypatch):
    t = {"Resources": {"B": {"Type": "AWS::S3::Bucket", "Properties": {"BucketName": "${file(x)}"}}}}
    for v in ("0", "false", "", "no"):
        monkeypatch.setenv("MINISTACK_CFN_FAIL_ON_CUSTOM_SYNTAX", v)
        assert warn_or_reject_custom_syntax(t) is None
