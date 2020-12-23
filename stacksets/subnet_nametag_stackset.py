from aws_cdk import (
    aws_ssm as ssm,
    aws_iam as iam,
    aws_cloudformation as cfn,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_s3 as s3,
    core
)

from common.var import *
import yaml

PARAMETER_FILE = PARAMETER.SUBNET
UPLOAD_BUCKET = BUCKET.UPLOADS3

class SubnetNameTagStacksetStack(core.Stack):

    def setTag(self, valueName, **kwargs):
        tagName = core.Token.as_any({
            "Key": "Name",
            "Value": valueName
        })
        tagArray = [tagName]

        for tKey, tValue in kwargs.items():
            tagArray.append(core.Token.as_any({
                "Key": tKey,
                "Value": tValue
            })
            )
        return tagArray

    def putParam(self, key, pname, pvalue):
        return ssm.CfnParameter(
            self,
            key,
            name = pname,
            type = "String",
            value = pvalue
        )

    def __init__(self, scope: core.Construct, id: str, props, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        ##############
        # parameters
        ##############

        with open(PARAMETER_FILE, 'r') as stream:
            try:
                params = yaml.safe_load(stream)
                # for item, doc in params.items():
                #     print(item, ":", doc)

            except yaml.YAMLError as e:
                print(e)

        params_map = {}
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
            params_map[item] = param

        vpcId = params_map["vpcId"]
        sharedAccountId = params_map["ShareToAccountId"]
        envName = params_map["EnvironmentName"]
        appName = params_map["ApplicationName"]
        publicSubnetAId = params_map["PublicSubnet1Id"]
        publicSubnetBId = params_map["PublicSubnet2Id"]
        privateWebSubnetACidr = params_map["PrivateWEBSubnet1CIDR"]
        privateWebSubnetBCidr = params_map["PrivateWEBSubnet2CIDR"]
        privateDbSubnetACidr = params_map["PrivateDBSubnet1CIDR"]
        privateDbSubnetBCidr = params_map["PrivateDBSubnet2CIDR"]

        privateWebSubnetA_tags = envName.value_as_string + "-private-" + appName.value_as_string + "-web-" + core.Fn.select(2, core.Fn.split(".", privateWebSubnetACidr.value_as_string)) + "-a"
        privateWebSubnetB_tags = envName.value_as_string + "-private-" + appName.value_as_string + "-web-" + core.Fn.select(2, core.Fn.split(".", privateWebSubnetBCidr.value_as_string)) + "-b"
        privateDbSubnetA_tags = envName.value_as_string + "-private-" + appName.value_as_string + "-db-" + core.Fn.select(2, core.Fn.split(".", privateDbSubnetACidr.value_as_string)) + "-a"
        privateDbSubnetB_tags = envName.value_as_string + "-private-" + appName.value_as_string + "-db-" + core.Fn.select(2, core.Fn.split(".", privateDbSubnetBCidr.value_as_string)) + "-b"
        rtWebA_tags = "rt-" + envName.value_as_string + "-private-" + appName.value_as_string + "-web" + "-a"
        rtWebB_tags = "rt-" + envName.value_as_string + "-private-" + appName.value_as_string + "-web" + "-b"
        rtDBA_tags = "rt-" + envName.value_as_string + "-private-" + appName.value_as_string + "-db" + "-a"
        rtDBB_tags = "rt-" + envName.value_as_string + "-private-" + appName.value_as_string + "-db" + "-b"
        netAclWeb_tags = envName.value_as_string + "-private-" + appName.value_as_string + "-web"
        netAclDB_tags = envName.value_as_string + "-private-" + appName.value_as_string + "-db"
        netAclPublic_tags = "PublicNetworkAcl"

        # if envName.value_as_string == "dev":
        #     vpc_tags = "dev-VPC"
        #     igw_tags = "dev-IGW"
        #     publicSubnetA_tags = "dev-public-mgmt-128-AZ1"
        #     publicSubnetC_tags = "dev-public-mgmt-129-AZ2"
        # else:
        #     vpc_tags = "prod-VPC"
        #     igw_tags = "prod-IGW"
        #     publicSubnetA_tags = "prod-public-mgmt-0-AZ1"
        #     publicSubnetC_tags = "prod-public-mgmt-1-AZ2"            

        self.putParam("ssmvpcId", "vpcId", vpcId.value_as_string)
        self.putParam("ssmpublicSubnetAId", "publicSubnetAId", publicSubnetAId.value_as_string)
        self.putParam("ssmpublicSubnetBId", "publicSubnetBId", publicSubnetBId.value_as_string)   
        self.putParam("ssmprivateWebSubnetACidr", "privateWebSubnetACidr", privateWebSubnetACidr.value_as_string)
        self.putParam("ssmprivateWebSubnetBCidr", "privateWebSubnetBCidr", privateWebSubnetBCidr.value_as_string)
        self.putParam("ssmprivateDbSubnetACidr", "privateDbSubnetACidr", privateDbSubnetACidr.value_as_string)
        self.putParam("ssmprivateDbSubnetBCidr", "privateDbSubnetBCidr", privateDbSubnetBCidr.value_as_string)
        self.putParam("ssmenvName", "envName", envName.value_as_string)
        self.putParam("ssmappName", "appName", appName.value_as_string)

        ##############
        # Resources
        ##############

        NameTaglambdaServiceRole = iam.CfnRole(
            self,
            "NameTagLambdaServiceRole",
            # role_name="NameTagLambdaServiceRole",
            assume_role_policy_document={
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        }
                    }
                ],
                "Version": "2012-10-17"
            },
            policies = [
            {
                "policyName" : "NameTagLambdaServicePolicy",
                "policyDocument" : {
                "Version":"2012-10-17",
                "Statement" : [
                {
                  "Effect": "Allow",
                  "Action" : [
                    "ec2:Describe*",
                    "ec2:CreateTags",
                    "ssm:PutParameter",
                    "ssm:GetParameter",
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents"
                  ],
                    "Resource": "*"
                },
                ]}
            }]
            )

        NameTaglambda_layer = _lambda.CfnLayerVersion(
            self,
            "NameTaglambda_layer",
            layer_name="NameTaglambda-layer",
            compatible_runtimes=['python3.6', 'python3.7', 'python3.8'],
            content=_lambda.CfnLayerVersion.ContentProperty(
                s3_bucket=UPLOAD_BUCKET,
                s3_key="requests_pack.zip"
            ),
            description="NameTaglambda layer",
            license_info="MIT"
        )

        NameTaglambdafunction = _lambda.CfnFunction(
            self,
            "NameTagFunction",
            runtime="python3.7",
            timeout = 120,
            handler="NameTag.handler",
            code=_lambda.CfnFunction.CodeProperty(
                s3_bucket=UPLOAD_BUCKET,
                s3_key="NameTag.zip"
            ),
            layers=[NameTaglambda_layer.ref],
            role=NameTaglambdaServiceRole.attr_arn,
            environment = {
                "variables" : {
#                    "vpc_tags" : vpc_tags,
#                    "igw_tags" : igw_tags,
#                    "publicSubnetA_tags" : publicSubnetA_tags,
#                    "publicSubnetC_tags" : publicSubnetC_tags,
                    "privateWebSubnetA_tags" : privateWebSubnetA_tags,                           
                    "privateWebSubnetB_tags" : privateWebSubnetB_tags,
                    "privateDbSubnetA_tags" : privateDbSubnetA_tags,
                    "privateDbSubnetB_tags" : privateDbSubnetB_tags,
                    "rtWebA_tags" : rtWebA_tags,
                    "rtWebB_tags" : rtWebB_tags,
                    "rtDBA_tags" : rtDBA_tags,
                    "rtDBB_tags" : rtDBB_tags,
                    "netAclWeb_tags" : netAclWeb_tags,
                    "netAclDB_tags" : netAclDB_tags,
                    "netAclPublic_tags" : netAclPublic_tags
                }
            }
        )

        NameTaglambdafunction.add_depends_on(NameTaglambdaServiceRole)

        core.CustomResource(
            self,
            "CallAccountTag",
            resource_type="Custom::CallAccountTag",
            service_token=NameTaglambdafunction.attr_arn
        )
        # cfn.CfnCustomResource(
        #     self,
        #     "CallAccountTag",
        #     service_token=NameTaglambdafunction.attr_arn
        # )