from aws_cdk import (
    aws_ssm as ssm,
    aws_ec2 as ec2,
    core
)

vpc_id = "vpc-028a187dad7264bf4"  # Import an Exist VPC
ec2_type = "t2.micro"
key_name = "JJ-DEV-EVENT"
# Refer to an Exist AMI
linux_ami = ec2.GenericLinuxImage({
    "ap-northeast-2": "ami-095ca789e0549777d"
})
with open("./products/user_data/user_data.sh") as f:
    user_data = f.read()


class BastionStack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # The code that defines your stack goes here
        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_id=vpc_id)

        for i in range(0, 2):
            idx = str(i)
            host = ec2.Instance(self, "myEC2" + idx,
                                instance_type=ec2.InstanceType(
                                    instance_type_identifier=ec2_type),
                                instance_name="mySingleHost" + idx,
                                machine_image=linux_ami,
                                vpc=vpc,
                                key_name=key_name,
                                # vpc_subnets=ec2.SubnetSelection(
                                #     subnet_type=ec2.SubnetType.PRIVATE),
                                user_data=ec2.UserData.custom(user_data)
                                )
            # host.instance.add_property_override("NetworkInterfaces", [{
            #     "AssociatePublicIpAddress": "false",
            #     "DeviceIndex": 0,
            #     "SubnetId": "subnet-027ab1b832df3d8df"
            # }])
            # ec2.Instance has no property of BlockDeviceMappings, add via lower layer cdk api:
            host.instance.add_property_override("BlockDeviceMappings", [{
                "DeviceName": "/dev/xvda",
                "Ebs": {
                    "VolumeSize": "10",
                    "VolumeType": "io1",
                    "Iops": "150",
                    "DeleteOnTermination": "true"
                }
            }, {
                "DeviceName": "/dev/sdb",
                "Ebs": {"VolumeSize": "10"}
            }
            ])  # by default VolumeType is gp2, VolumeSize 8GB
            # host.connections.allow_from_any_ipv4(
            #     ec2.Port.tcp(22), "Allow ssh from internet")
            # host.connections.allow_from_any_ipv4(
            #     ec2.Port.tcp(80), "Allow http from internet")

        # core.CfnOutput(self, "Output",
        #                value=host.instance_public_ip)
