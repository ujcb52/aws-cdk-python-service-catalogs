from aws_cdk import (
    core
)
import yaml
from common.cdk_common import *
from common.var import *

# # Start - Case : 1
# from typing_extensions import Protocol
# # END - Case : 1

#ACCOUNT_ID = ACCOUNT.SHARED
STACKSET_URL = "https://" + BUCKET.CREATED + ".s3.ap-northeast-2.amazonaws.com/stacksets/cfn/subnet-stackset.yaml"
STACKSET_NAMETAG_URL = "https://" + BUCKET.CREATED + ".s3.ap-northeast-2.amazonaws.com/stacksets/cfn/subnet-nametag-stackset.yaml"
STACKSET_NAME = "subnet-stackset"

PARAMETER_FILE = PARAMETER.SUBNET


class SubnetProductStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

# Error? - Start - Case : 1
#   File "/Users/a1101167/aws-devel/dev-lz/python-service-catalogs/.env/lib/python3.7/site-packages/typing_extensions.py", line 1545, in _no_init
#    raise TypeError('Protocols cannot be instantiated')
#TypeError: Protocols cannot be instantiated
        # class ProtoSubclass(Protocol):
        #     def __init__(self):
        #         core.ITemplateOptions(self,
        #             template_format_version="2010-09-09"
        #         )
## - End - Case : 1

        core.CfnMapping(
            self,
            id="LambdaFunction",
            mapping={
                "Logging": {
                    "Level": "info"
                }
            }
        )

        accountId = cfnParam(core, self, "AccountId", ACCOUNT.SHARED, "Shared Account Number")
        region = cfnParam(core, self, "Region", REGION.SEOUL, "Target region for VPC")
        stacksetName = cfnParam(core, self, "StackSetName", "Stackset-Subnets", "Stack Set Name for Shared Services Subnet")
        stacksetNameTag = cfnParam(core, self, "StackSetNameTag", "Stackset-SubnetNameTag", "Stack Set Name for Subnet NameTag")

        ### through parameters
        params_list, params_map, paramObj = getStackParams(core, self, PARAMETER_FILE)

        #accountIdNameTag = cfnParam(core, self, "accountIdNameTag", params_map["ShareToAccountId"], "Shared To Account Number")
        accountIdDev = params_map["ShareToAccountId"]

        # core.ITemplateOptions.metadata = {
        self.template_options.metadata = {
            'ParameterGroups': [
                {
                    'Label': {'default': 'Target Account Information'},
                    'Parameters': [accountId.logical_id]
                },
                {
                    'Label': {'default': 'Region to deploy the VPC'},
                    'Parameters': [region.logical_id]
                },
                {
                    'Label': {'default': 'VPC Details'},
                    'Parameters': params_list
                }
            ]

        }

        core.CustomResource(
            self,
            "SSMGetParameters",
            resource_type="Custom::SSMParameters",
            properties={
                "SSMParameterKeys": [
                    "/org/primary/service_catalog/bucket_name",
                    "/org/primary/account_id",
                    "/org/primary/organization_id"
                ]
            },
            service_token=core.Fn.sub(
                body="arn:aws:lambda:ap-northeast-2:${AWS::AccountId}:function:LandingZone"
            )
            # "arn:aws:lambda:ap-northeast-2:" + ACCOUNT.MASTER + ":function:LandingZone"

        )

        core.CustomResource(
            self,
            "StackSetSharedServicesSubnetStackSet",
            resource_type="Custom::StackInstance",
            properties={
                "StackSetName": stacksetName.value_as_string + "-" + paramObj["EnvironmentName"].value_as_string + "-" +
                                paramObj["ApplicationName"].value_as_string,
                "TemplateURL": STACKSET_URL,
                "AccountList": [accountId.value_as_string],
                "RegionList": [region.value_as_string],
                "Parameters": params_map,
                "Capabilities": "CAPABILITY_NAMED_IAM",
                # "ServiceToken": core.Fn.join(
                #     delimiter=":",
                #     list_of_values=[
                #         "arn:aws:lambda:ap-northeast-2:",
                #         core.Fn.ref(logical_name="AWS::AccountId"),
                #         "function:LandingZone"
                #     ]
                # )
                "ServiceToken": "arn:aws:lambda:ap-northeast-2:" + ACCOUNT.MASTER + ":function:LandingZone"
            },
            # service_token=core.Fn.join(
            #     delimiter=":",
            #     list_of_values=[
            #         "arn:aws:lambda:ap-northeast-2:",
            #         core.Fn.ref(logical_name="AWS::AccountId"),
            #         "function:LandingZone"
            #     ]
            # )
            service_token="arn:aws:lambda:ap-northeast-2:" + ACCOUNT.MASTER + ":function:LandingZone"

        )

        core.CustomResource(
            self,
            "StackSetSubnetNameTagStackSet",
            resource_type="Custom::StackInstance",
            properties={
                "StackSetName": stacksetNameTag.value_as_string + "-" + paramObj["EnvironmentName"].value_as_string + "-" +
                                paramObj["ApplicationName"].value_as_string,
                "TemplateURL": STACKSET_NAMETAG_URL,
                "AccountList": [accountIdDev],
                "RegionList": [region.value_as_string],
                "Parameters": params_map,
                "Capabilities": "CAPABILITY_NAMED_IAM",
                "ServiceToken": "arn:aws:lambda:ap-northeast-2:" + ACCOUNT.MASTER + ":function:LandingZone"
            },
            service_token="arn:aws:lambda:ap-northeast-2:" + ACCOUNT.MASTER + ":function:LandingZone"
        )