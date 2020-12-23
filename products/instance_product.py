from aws_cdk import (
    core
)
import yaml
from common.cdk_common import *
from common.var import *

ACCOUNT_ID = ACCOUNT.SHARED
STACKSET_URL = "https://" + BUCKET.CREATED + ".s3.ap-northeast-2.amazonaws.com/stacksets/cfn/instance-stackset.yaml"
STACKSET_NAME = "instance-stackset"

PARAMETER_FILE = PARAMETER.INSTANCE


class InstanceProductStack(core.Stack):

    def cfnParam(self, key, defaultValue, desc):
        return core.CfnParameter(self,
                                 id=key,
                                 type="String",
                                 default=defaultValue,
                                 description=desc
                                 )

    def getStackParams(self, filePath):
        # read yaml file
        with open(filePath, 'r') as stream:
            try:
                params = yaml.safe_load(stream)
            except yaml.YAMLError as e:
                print(e)

        list = []
        map = {}
        paramObj = {}
        for item, doc in params.items():
            if "AllowedValues" in doc:
                param = core.CfnParameter(self,
                                          id=item,
                                          type=doc["Type"],
                                          default=doc["Default"],
                                          description=doc["Description"],
                                          allowed_values=doc.get("AllowedValues")
                                          )
            else:
                param = core.CfnParameter(self,
                                          id=item,
                                          type=doc["Type"],
                                          default=doc["Default"],
                                          description=doc["Description"]
                                          )
            list.append(param.logical_id)
            map[item] = param.value_as_string
            paramObj[item] = param

        return list, map, paramObj

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
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

        accountId = self.cfnParam("AccountId", ACCOUNT.SHARED, "Target Account Number")
        region = self.cfnParam("Region", REGION.SEOUL, "Target region for VPC")
        stacksetName = self.cfnParam("StackSetName", "Stackset-Instances", "Stack Set Name for Instances")

        ### through parameters
        params_list, params_map, paramObj = self.getStackParams(PARAMETER_FILE)

        # core.ITemplateOptions.metadata = {
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