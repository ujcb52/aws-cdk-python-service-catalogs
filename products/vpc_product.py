from aws_cdk import (
    core
)
import yaml
from common.cdk_common import *
from common.var import *

#ACCOUNT_ID = ACCOUNT.MASTER
ACCOUNT_ID = ACCOUNT.SHARED
STACKSET_URL = "https://" + BUCKET.CREATED + ".s3.ap-northeast-2.amazonaws.com/stacksets/cfn/vpc-stackset.yaml"
STACKSET_NAME = "vpc-stackset"

PARAMETER_FILE = PARAMETER.VPC


class VpcProductStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        core.CfnMapping(
            self,
            id="LambdaFunction",
            mapping={
                "Logging": {
                    "Level": "info"
                }
            }
        )

        accountId = cfnParam(core, self, "AccountId", ACCOUNT.SHARED, "Target Account Number")
        region = cfnParam(core, self, "Region", REGION.SEOUL, "Target region for VPC")
        stacksetName = cfnParam(core, self, "StackSetName", "Stackset-vpc", "Stack Set Name for Shared Services vpc")

        ### through parameters
        params_list, params_map, paramObj = getStackParams(core, self, PARAMETER_FILE)

        #core.ITemplateOptions.metadata = {
        self.template_options.metadata = {
            'ParameterGroups': [
                {
                    'Label': {'default': 'Target Account Information'},
                    'Parameters': [accountId]
                },
                {
                    'Label': {'default': 'Region to deploy the VPC'},
                    'Parameters': [region]
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
                    "/org/primary/organization_id",
                    "/org/member/sharedservices/tgw_id"
                ]
            },
            service_token=core.Fn.sub(
                body="arn:aws:lambda:ap-northeast-2:${AWS::AccountId}:function:LandingZone"
            )            
#            service_token="arn:aws:lambda:ap-northeast-2:" + ACCOUNT_ID + ":function:LandingZone"

        )
        core.CustomResource(
            self,
            "StackSetSharedServicesVPCStackSet",
            resource_type="Custom::StackInstance",
            properties={
#                "StackSetName": "JJ_stackset",
                "StackSetName": stacksetName.value_as_string + "-" + paramObj["EnvironmentName"].value_as_string + "-" +
                                paramObj["ApplicationName"].value_as_string,
                "TemplateURL": STACKSET_URL,
                "AccountList": accountId.value_as_string,
                "RegionList": region.value_as_string,
#                "Parameters": {
#                    "vpcCidr": vpcCidr.value_as_string
#                },
                "Parameters": params_map,
                "Capabilities": "CAPABILITY_NAMED_IAM",
                "ServiceToken": "arn:aws:lambda:ap-northeast-2:" + ACCOUNT.MASTER + ":function:LandingZone"
            },
            service_token="arn:aws:lambda:ap-northeast-2:" + ACCOUNT.MASTER + ":function:LandingZone"

        )
