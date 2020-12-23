from aws_cdk import (
    aws_servicecatalog as sc,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_cloudformation as cfn,
    aws_ec2 as ec2,
    core
)


class VpcStacksetStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        cidr = core.CfnParameter(self,
                                 id="vpcCidr",
                                 type="String",
                                 default="10.0.0.0/16",
                                 # allowed_pattern='(\\d{1,3})\.(\\d{1,3})\.(\\d{1,3})\.(\\d{1,3})/(\\d{1,2})',
                                 description="CIDR for vpc.")
        ec2.CfnVPC(self,
                   id="VPC",
                   cidr_block=cidr.value_as_string,
                   enable_dns_hostnames=True,
                   enable_dns_support=True
                   )
        # ec2.Vpc(
        #     self,
        #     id="JJVPC",
        #     # cidr="10.0.0.0/16"
        #     cidr=cidr.value_as_string
        # )
        return
