from aws_cdk import (
    aws_servicecatalog as sc,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_cloudformation as cfn,
    aws_ec2 as ec2,
    aws_ram as ram,
    core
)

from common.var import *
import yaml

PARAMETER_FILE = PARAMETER.SUBNET


class InstanceStacksetStack(core.Stack):


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
        publicSubnetCId = params_map["PublicSubnet2Id"]

        privateWebSubnetACidr = params_map["PrivateWEBSubnet1CIDR"]
        privateWebSubnetCCidr = params_map["PrivateWEBSubnet2CIDR"]

        privateDbSubnetACidr = params_map["PrivateDBSubnet1CIDR"]
        privateDbSubnetCCidr = params_map["PrivateDBSubnet2CIDR"]

        isCreateEndpoints = params_map["CreateEndpoints"]
        isCreateNatGateway = params_map["CreateNatGateway"]

        existNatIdA = params_map["ExistNatGatewayID1"]
        existNatIdC = params_map["ExistNatGatewayID2"]
        isConnectTgw = params_map["ConnectTransitGateway"]
        existTgw = params_map["ExistTransitGateway"]

        ##############
        # Resources
        ##############

        PrivateWebSubnetA = self.privateSubnet("PrivateWebSubnetA", "a", privateWebSubnetACidr.value_as_string,
                                               vpcId.value_as_string)
        PrivateWebSubnetC = self.privateSubnet("PrivateWebSubnetC", "c", privateWebSubnetCCidr.value_as_string,
                                               vpcId.value_as_string)

        PrivateDbSubnetA = self.privateSubnet("PrivateDbSubnetA", "a", privateDbSubnetACidr.value_as_string,
                                              vpcId.value_as_string)
        PrivateDbSubnetC = self.privateSubnet("PrivateDbSubnetC", "c", privateDbSubnetCCidr.value_as_string,
                                              vpcId.value_as_string)

        tagArray = self.setTag(
            envName.value_as_string + "-private-" + appName.value_as_string + "-web-" + core.Fn.select(
                2, core.Fn.split(".", privateWebSubnetACidr.value_as_string)) + "-a")
        PrivateWebSubnetA.add_property_override("Tags", tagArray)
        tagArray = self.setTag(
            envName.value_as_string + "-private-" + appName.value_as_string + "-web-" + core.Fn.select(
                2, core.Fn.split(".", privateWebSubnetCCidr.value_as_string)) + "-c")
        PrivateWebSubnetC.add_property_override("Tags", tagArray)
        tagArray = self.setTag(
            envName.value_as_string + "-private-" + appName.value_as_string + "-db-" + core.Fn.select(
                2, core.Fn.split(".", privateDbSubnetACidr.value_as_string)) + "-a")
        PrivateDbSubnetA.add_property_override("Tags", tagArray)
        tagArray = self.setTag(
            envName.value_as_string + "-private-" + appName.value_as_string + "-db-" + core.Fn.select(
                2, core.Fn.split(".", privateDbSubnetCCidr.value_as_string)) + "-c")
        PrivateDbSubnetC.add_property_override("Tags", tagArray)

        rtA = self.routeTable("PrivateRouteTableWebA", vpcId.value_as_string)
        rtC = self.routeTable("PrivateRouteTableWebC", vpcId.value_as_string)
        rtDB = self.routeTable("PrivateRouteTableDB", vpcId.value_as_string)

        rtA.add_property_override("Tags",
                                  self.setTag("rt-pri-web-a" + appName.value_as_string + "-" + envName.value_as_string))
        rtC.add_property_override("Tags",
                                  self.setTag("rt-pri-web-c" + appName.value_as_string + "-" + envName.value_as_string))
        rtDB.add_property_override("Tags",
                                   self.setTag("rt-pri-db" + appName.value_as_string + "-" + envName.value_as_string))

        # ec2.SubnetSelection(
        #     subnet_name="PrivateWebSubnetA",
        #     subnet_group_name=
        # )
        rtAssoA = self.rtAssociation("PrivateWebSubnetARouteTableAssociation", rtA.ref, PrivateWebSubnetA.ref)
        rtAssoC = self.rtAssociation("PrivateWebSubnetCRouteTableAssociation", rtC.ref, PrivateWebSubnetC.ref)
        rtAssoDBA = self.rtAssociation("PrivateDbSubnetARouteTableAssociation", rtDB.ref, PrivateDbSubnetA.ref)
        rtAssoDBC = self.rtAssociation("PrivateDbSubnetCRouteTableAssociation", rtDB.ref, PrivateDbSubnetC.ref)

        netAcl = ec2.CfnNetworkAcl(self,
                                   id="PrivateNetworkAcl",
                                   vpc_id=vpcId.value_as_string
                                   )

        netAcl.add_property_override("Tags",
                                     self.setTag("PrivateNetworkAcl"))

        ec2.CfnNetworkAclEntry(self,
                               id="PrivateNetworkAclIngressEntry100",
                               network_acl_id=netAcl.ref,
                               protocol=-1,
                               rule_action="allow",
                               rule_number=100,
                               egress=False,
                               cidr_block="0.0.0.0/0",
                               icmp={
                                   "code": -1,
                                   "type": -1
                               },
                               port_range={
                                   "from": 0,
                                   "to": 65535
                               }
                               )

        ec2.CfnNetworkAclEntry(self,
                               id="PrivateNetworkAclEgressEntry100",
                               network_acl_id=netAcl.ref,
                               protocol=-1,
                               rule_action="allow",
                               rule_number=100,
                               egress=True,
                               cidr_block="0.0.0.0/0",
                               icmp={
                                   "code": -1,
                                   "type": -1
                               },
                               port_range={
                                   "from": 0,
                                   "to": 65535
                               }
                               )

        netAclAssoA = ec2.CfnSubnetNetworkAclAssociation(self,
                                                         id="PrivateNetworkAclAssociationA",
                                                         subnet_id=PrivateWebSubnetA.ref,
                                                         network_acl_id=netAcl.ref
                                                         )
        netAclAssoC = ec2.CfnSubnetNetworkAclAssociation(self,
                                                         id="PrivateNetworkAclAssociationC",
                                                         subnet_id=PrivateWebSubnetC.ref,
                                                         network_acl_id=netAcl.ref
                                                         )

        netAclAssoA.add_depends_on(PrivateWebSubnetA)
        netAclAssoC.add_depends_on(PrivateWebSubnetC)

        isEndPoint = core.CfnCondition(self,
                                       id="CondCreateEndpoints",
                                       expression=core.Fn.condition_equals(isCreateEndpoints, YN.YES)
                                       )
        isNat = core.CfnCondition(self,
                                  id="CondCreateNatGateway",
                                  expression=core.Fn.condition_equals(isCreateNatGateway, YN.YES)
                                  )
        isTgw = core.CfnCondition(self,
                                  id="CondConnectTransitGateway",
                                  expression=core.Fn.condition_equals(isConnectTgw, YN.YES)
                                  )

        eipA = ec2.CfnEIP(self,
                          id="EipA",
                          domain="vpc"
                          )
        eipC = ec2.CfnEIP(self,
                          id="EipC",
                          domain="vpc"
                          )
        eipA.add_override("Condition", isNat.logical_id)
        eipC.add_override("Condition", isNat.logical_id)

        natA = ec2.CfnNatGateway(self,
                                 id="NatGatewayA",
                                 allocation_id=eipA.attr_allocation_id,
                                 subnet_id=publicSubnetAId.value_as_string
                                 )
        natC = ec2.CfnNatGateway(self,
                                 id="NatGatewayC",
                                 allocation_id=eipC.attr_allocation_id,
                                 subnet_id=publicSubnetCId.value_as_string
                                 )
        natA.add_override("Condition", isNat.logical_id)
        natC.add_override("Condition", isNat.logical_id)

        natA.add_property_override("Tags",
                                   self.setTag("nat-a-" + appName.value_as_string + "-" + envName.value_as_string,
                                               Application=appName.value_as_string,
                                               Environment=envName.value_as_string))
        natC.add_property_override("Tags",
                                   self.setTag("nat-c-" + appName.value_as_string + "-" + envName.value_as_string,
                                               Application=appName.value_as_string,
                                               Environment=envName.value_as_string))

        ec2.CfnRoute(self,
                     id="PrivateRouteToInternetA",
                     route_table_id=rtA.ref,
                     destination_cidr_block="0.0.0.0/0",
                     nat_gateway_id=core.Fn.condition_if(isNat.logical_id, natA.ref,
                                                         existNatIdA.value_as_string).to_string()
                     )

        ec2.CfnRoute(self,
                     id="PrivateRouteToInternetC",
                     route_table_id=rtC.ref,
                     destination_cidr_block="0.0.0.0/0",
                     nat_gateway_id=core.Fn.condition_if(isNat.logical_id, natC.ref,
                                                         existNatIdC.value_as_string).to_string()
                     )

        cidrList = [
            "172.18.0.0/16",
            "172.28.0.0/16",
            "10.205.0.0/16",
            "10.40.0.0/16",
            "172.19.0.0/16",
            "172.29.0.0/16",
            "172.20.0.0/16",
            "10.10.100.0/24",
            "10.10.136.0/22",
            "10.10.88.0/23",
            "10.10.160.0/21"
        ]
        self.routeTgw("PrivateRouteAToTGW", rtA.ref, existTgw.value_as_string, cidrList, isTgw.logical_id)
        self.routeTgw("PrivateRouteCToTGW", rtC.ref, existTgw.value_as_string, cidrList, isTgw.logical_id)
        self.routeTgw("PrivateRouteDBToTGW", rtDB.ref, existTgw.value_as_string, cidrList, isTgw.logical_id)

        shareRes = ram.CfnResourceShare(self,
                                        id="SubnetShare",
                                        name="RAM-Subnet-" + appName.value_as_string + "-" + envName.value_as_string,
                                        principals=[sharedAccountId.value_as_string],
                                        resource_arns=[
                                            "arn:aws:ec2:" + REGION.SEOUL + ":" + ACCOUNT.SHARED + ":subnet/" + PrivateWebSubnetA.ref,
                                            "arn:aws:ec2:" + REGION.SEOUL + ":" + ACCOUNT.SHARED + ":subnet/" + PrivateWebSubnetC.ref,
                                            "arn:aws:ec2:" + REGION.SEOUL + ":" + ACCOUNT.SHARED + ":subnet/" + PrivateDbSubnetA.ref,
                                            "arn:aws:ec2:" + REGION.SEOUL + ":" + ACCOUNT.SHARED + ":subnet/" + PrivateDbSubnetC.ref
                                        ]
                                        )
        shareRes.add_property_override("Tags", self.setTag("ShareTo-" + sharedAccountId.value_as_string,
                                                           Application=appName.value_as_string,
                                                           Environment=envName.value_as_string))

        sgVpcEndpoint = ec2.CfnSecurityGroup(self,
                                             id="VPCEndpointSecurityGroup",
                                             vpc_id=vpcId.value_as_string,
                                             group_description="Allow VPCEndpoints - Interfaces",
                                             security_group_ingress=[
                                                 core.Token.as_any(
                                                     {
                                                         "ipProtocol": "-1",
                                                         "fromPort": -1,
                                                         "toPort": -1,
                                                         "cidrIp": "0.0.0.0/0"
                                                     })
                                             ],
                                             security_group_egress=[
                                                 core.Token.as_any(
                                                     {
                                                         "ipProtocol": "-1",
                                                         "fromPort": -1,
                                                         "toPort": -1,
                                                         "cidrIp": "0.0.0.0/0"
                                                     })
                                             ]
                                             )

        sgVpcEndpoint.add_property_override("Tags", self.setTag(
            "SG-VPCENDPOINT-" + appName.value_as_string + "-" + envName.value_as_string))

        sgList = [sgVpcEndpoint.ref]
        subnetList = [
            PrivateWebSubnetA.ref,
            PrivateWebSubnetC.ref
        ]
        epEc2Msg = self.vpcEndpoint("EndpointEC2Messages", sgList,
                                    "com.amazonaws." + REGION.SEOUL + ".ec2messages",
                                    vpcId.value_as_string,
                                    subnetList
                                    )
        epSsm = self.vpcEndpoint("EndpointSSM", sgList,
                                 "com.amazonaws." + REGION.SEOUL + ".ssm",
                                 vpcId.value_as_string,
                                 subnetList
                                 )

        epSsmMsg = self.vpcEndpoint("EndpointSSMMessage", sgList,
                                    "com.amazonaws." + REGION.SEOUL + ".ssmmessages",
                                    vpcId.value_as_string,
                                    subnetList
                                    )

        plcyDoc = """
{
"Version":"2012-10-17",
"Statement":[{
  "Effect":"Allow",
  "Principal": "*",
  "Action":["s3:GetObject*","s3:ListAllMyBuckets","s3:ListObject*"],
  "Resource":["arn:aws:s3:::*/*"]
}]
}
      """
        epS3 = ec2.CfnVPCEndpoint(self,
                                  id="EndportS3",
                                  service_name="com.amazonaws." + REGION.SEOUL + ".s3",
                                  vpc_id=vpcId.value_as_string,
                                  route_table_ids=[
                                      rtA.ref,
                                      rtC.ref
                                  ]
                                  )
        epS3.add_override("Properties.PolicyDocument", plcyDoc)

        epS3.add_override("Condition", isEndPoint.logical_id)

        sgVpcEndpoint.add_override("Condition", isEndPoint.logical_id)
        epEc2Msg.add_override("Condition", isEndPoint.logical_id)
        epSsm.add_override("Condition", isEndPoint.logical_id)
        epSsmMsg.add_override("Condition", isEndPoint.logical_id)

        #### additional Security Group

        sgDefaultSubnet = ec2.CfnSecurityGroup(self,
                                               id="PrivateSubnetSecurityGroup",
                                               vpc_id=vpcId.value_as_string,
                                               group_description="Allow VPCEndpoints - Interfaces",
                                               security_group_ingress=[
                                                   core.Token.as_any(
                                                       {
                                                           "ipProtocol": "icmp",
                                                           "fromPort": -1,
                                                           "toPort": -1,
                                                           "cidrIp": "0.0.0.0/0"
                                                       }),
                                                   core.Token.as_any(
                                                       {
                                                           "ipProtocol": "tcp",
                                                           "fromPort": 22,
                                                           "toPort": 22,
                                                           "cidrIp": "10.192.0.0/24"
                                                       }),
                                                   core.Token.as_any(
                                                       {
                                                           "ipProtocol": "tcp",
                                                           "fromPort": 80,
                                                           "toPort": 80,
                                                           "cidrIp": "100.64.0.0/17"
                                                       }),
                                                   core.Token.as_any(
                                                       {
                                                           "ipProtocol": "tcp",
                                                           "fromPort": 443,
                                                           "toPort": 443,
                                                           "cidrIp": "100.64.0.0/17"
                                                       }),
                                                   core.Token.as_any(
                                                       {
                                                           "ipProtocol": "tcp",
                                                           "fromPort": 8080,
                                                           "toPort": 8080,
                                                           "cidrIp": "100.64.0.0/17"
                                                       })
                                               ],
                                               security_group_egress=[
                                                   core.Token.as_any(
                                                       {
                                                           "ipProtocol": "-1",
                                                           "fromPort": -1,
                                                           "toPort": -1,
                                                           "cidrIp": "0.0.0.0/0"
                                                       }),
                                                   core.Token.as_any(
                                                       {
                                                           "ipProtocol": "icmp",
                                                           "fromPort": -1,
                                                           "toPort": -1,
                                                           "cidrIp": "0.0.0.0/0"
                                                       })

                                               ]
                                               )

        addTag = {"i11::target-account-id": sharedAccountId.value_as_string}
        sgDefaultSubnet.add_property_override("Tags", self.setTag(
            "SG-DEFAULT-" + appName.value_as_string + "-" + envName.value_as_string,
            **addTag
        ))

    def vpcEndpoint(self, key, sgList, svcName, vpc, subnetList):
        return ec2.CfnVPCEndpoint(self,
                                  id=key,
                                  security_group_ids=sgList,
                                  vpc_endpoint_type="Interface",
                                  service_name=svcName,
                                  private_dns_enabled=True,
                                  vpc_id=vpc,
                                  subnet_ids=subnetList
                                  )

    def routeTgw(self, key, rt, tgw, cidrList, condition):
        for i, cidr in enumerate(cidrList):
            tmp = ec2.CfnRoute(self,
                               id=key + str(i),
                               route_table_id=rt,
                               destination_cidr_block=cidr,
                               transit_gateway_id=tgw
                               )
            tmp.add_override("Condition", condition)

    def rtAssociation(self, key, rtId, subnetId):
        return ec2.CfnSubnetRouteTableAssociation(self,
                                                  id=key,
                                                  route_table_id=rtId,
                                                  subnet_id=subnetId
                                                  )

    def privateSubnet(self, key, az, cidr, vpc, **kwargs):
        return ec2.CfnSubnet(self,
                             id=key,
                             availability_zone=REGION.SEOUL + az,
                             cidr_block=cidr,
                             vpc_id=vpc,
                             map_public_ip_on_launch=False
                             )

    def routeTable(self, key, vpc):
        return ec2.CfnRouteTable(self,
                                 id=key,
                                 vpc_id=vpc
                                 )
