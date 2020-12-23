from aws_cdk import (
    aws_servicecatalog as sc,
    aws_ssm as ssm,
    aws_iam as iam,
    aws_cloudformation as cfn,
    aws_ec2 as ec2,
    aws_ram as ram,
    aws_lambda as _lambda,
    core
)

from common.var import *
import yaml

PARAMETER_FILE = PARAMETER.SUBNET
UPLOAD_BUCKET = BUCKET.UPLOADS3


class SubnetStacksetStack(core.Stack):

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
        #privateWebSubnetCCidr = params_map["PrivateWEBSubnet3CIDR"]
        privateWebSubnetBCidr = params_map["PrivateWEBSubnet2CIDR"]
        privateDbSubnetACidr = params_map["PrivateDBSubnet1CIDR"]
        #privateDbSubnetCCidr = params_map["PrivateDBSubnet3CIDR"]
        privateDbSubnetBCidr = params_map["PrivateDBSubnet2CIDR"]
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
        # PrivateWebSubnetC = self.privateSubnet("PrivateWebSubnetC", "c", privateWebSubnetCCidr.value_as_string,
        #                                        vpcId.value_as_string)
        PrivateWebSubnetB = self.privateSubnet("PrivateWebSubnetB", "b", privateWebSubnetBCidr.value_as_string,
                                               vpcId.value_as_string)

        PrivateDbSubnetA = self.privateSubnet("PrivateDbSubnetA", "a", privateDbSubnetACidr.value_as_string,
                                              vpcId.value_as_string)
        # PrivateDbSubnetC = self.privateSubnet("PrivateDbSubnetC", "c", privateDbSubnetCCidr.value_as_string,
        #                                       vpcId.value_as_string)
        PrivateDbSubnetB = self.privateSubnet("PrivateDbSubnetB", "b", privateDbSubnetBCidr.value_as_string,
                                              vpcId.value_as_string)

        tagArray = self.setTag(
            envName.value_as_string + "-private-" + appName.value_as_string + "-web-" + core.Fn.select(
                2, core.Fn.split(".", privateWebSubnetACidr.value_as_string)) + "-a")
        PrivateWebSubnetA.add_property_override("Tags", tagArray)
        # tagArray = self.setTag(
        #     envName.value_as_string + "-private-" + appName.value_as_string + "-web-" + core.Fn.select(
        #        2, core.Fn.split(".", privateWebSubnetCCidr.value_as_string)) + "-c")
        # PrivateWebSubnetC.add_property_override("Tags", tagArray)
        tagArray = self.setTag(
            envName.value_as_string + "-private-" + appName.value_as_string + "-web-" + core.Fn.select(
                2, core.Fn.split(".", privateWebSubnetBCidr.value_as_string)) + "-b")
        PrivateWebSubnetB.add_property_override("Tags", tagArray)        
        tagArray = self.setTag(
            envName.value_as_string + "-private-" + appName.value_as_string + "-db-" + core.Fn.select(
                2, core.Fn.split(".", privateDbSubnetACidr.value_as_string)) + "-a")
        PrivateDbSubnetA.add_property_override("Tags", tagArray)
        # tagArray = self.setTag(
        #     envName.value_as_string + "-private-" + appName.value_as_string + "-db-" + core.Fn.select(
        #         2, core.Fn.split(".", privateDbSubnetCCidr.value_as_string)) + "-c")
        # PrivateDbSubnetC.add_property_override("Tags", tagArray)
        tagArray = self.setTag(
            envName.value_as_string + "-private-" + appName.value_as_string + "-db-" + core.Fn.select(
                2, core.Fn.split(".", privateDbSubnetBCidr.value_as_string)) + "-b")
        PrivateDbSubnetB.add_property_override("Tags", tagArray)

        rtA = self.routeTable("PrivateRouteTableWebA", vpcId.value_as_string)
        # rtC = self.routeTable("PrivateRouteTableWebC", vpcId.value_as_string)
        rtB = self.routeTable("PrivateRouteTableWebB", vpcId.value_as_string)
        rtDBA = self.routeTable("PrivateRouteTableDBA", vpcId.value_as_string)
        # rtDBC = self.routeTable("PrivateRouteTableDBC", vpcId.value_as_string)
        rtDBB = self.routeTable("PrivateRouteTableDBB", vpcId.value_as_string)

        rtA.add_property_override("Tags",
                                  self.setTag("rt-" + envName.value_as_string + "-private-" + appName.value_as_string + "-web" + "-a"))
        # rtC.add_property_override("Tags",
        #                           self.setTag("rt-" + envName.value_as_string + "-private-" + appName.value_as_string + "-web" + "-c"))
        rtB.add_property_override("Tags",
                                  self.setTag("rt-" + envName.value_as_string + "-private-" + appName.value_as_string + "-web" + "-b"))
        rtDBA.add_property_override("Tags",
                                   self.setTag("rt-" + envName.value_as_string + "-private-" + appName.value_as_string + "-db" + "-a"))
        # rtDBC.add_property_override("Tags",
        #                            self.setTag("rt-" + envName.value_as_string + "-private-" + appName.value_as_string + "-db" + "-c"))
        rtDBB.add_property_override("Tags",
                                   self.setTag("rt-" + envName.value_as_string + "-private-" + appName.value_as_string + "-db" + "-b"))
             
        # ec2.SubnetSelection(
        #     subnet_name="PrivateWebSubnetA",
        #     subnet_group_name=
        # )

        rtAssoA = self.rtAssociation("PrivateWebSubnetARouteTableAssociation", rtA.ref, PrivateWebSubnetA.ref)
        # rtAssoC = self.rtAssociation("PrivateWebSubnetCRouteTableAssociation", rtC.ref, PrivateWebSubnetC.ref)
        rtAssoB = self.rtAssociation("PrivateWebSubnetBRouteTableAssociation", rtB.ref, PrivateWebSubnetB.ref)        
        rtAssoDBA = self.rtAssociation("PrivateDbSubnetARouteTableAssociation", rtDBA.ref, PrivateDbSubnetA.ref)
        # rtAssoDBC = self.rtAssociation("PrivateDbSubnetCRouteTableAssociation", rtDBC.ref, PrivateDbSubnetC.ref)
        rtAssoDBB = self.rtAssociation("PrivateDbSubnetBRouteTableAssociation", rtDBB.ref, PrivateDbSubnetB.ref)        

        netAcl = self.NetworkAcl("PrivateNetworkAcl", vpcId.value_as_string)
        netAcl2 = self.NetworkAcl("PrivateNetworkAcl2", vpcId.value_as_string)

        netAcl.add_property_override("Tags",
                                     self.setTag(envName.value_as_string + "-private-" + appName.value_as_string + "-web"))
        netAcl2.add_property_override("Tags",
                                     self.setTag(envName.value_as_string + "-private-" + appName.value_as_string + "-db"))

        self.NetworkAclEntry("PrivateWebNAclIngressEntry100", netAcl.ref, False)
        self.NetworkAclEntry("PrivateWebNAclEgressEntry100", netAcl.ref, True)
        self.NetworkAclEntry("PrivateDBNAclIngressEntry100", netAcl2.ref, False)
        self.NetworkAclEntry("PrivateDBNAclEgressEntry100", netAcl2.ref, True)

        netAclAssoA = self.NAclAssociation("PrivateNAclAssociationA", PrivateWebSubnetA.ref, netAcl.ref)
        #netAclAssoC = self.NAclAssociation("PrivateNAclAssociationC", PrivateWebSubnetC.ref, netAcl.ref)
        netAclAssoB = self.NAclAssociation("PrivateNAclAssociationB", PrivateWebSubnetB.ref, netAcl.ref)
        netAclAssoDBA = self.NAclAssociation("PrivateDbNAclAssociationA", PrivateDbSubnetA.ref, netAcl2.ref)
        #netAclAssoDBC = self.NAclAssociation("PrivateDbNAclAssociationC", PrivateDbSubnetC.ref, netAcl2.ref)
        netAclAssoDBB = self.NAclAssociation("PrivateDbNAclAssociationB", PrivateDbSubnetB.ref, netAcl2.ref)

        netAclAssoA.add_depends_on(PrivateWebSubnetA)
        #netAclAssoC.add_depends_on(PrivateWebSubnetC)
        netAclAssoB.add_depends_on(PrivateWebSubnetB)
        netAclAssoDBA.add_depends_on(PrivateDbSubnetA)
        #netAclAssoDBC.add_depends_on(PrivateDbSubnetC)
        netAclAssoDBB.add_depends_on(PrivateDbSubnetB)

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
                                   self.setTag("nat-b-" + appName.value_as_string + "-" + envName.value_as_string,
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
                     route_table_id=rtB.ref,
                     destination_cidr_block="0.0.0.0/0",
                     nat_gateway_id=core.Fn.condition_if(isNat.logical_id, natC.ref,
                                                         existNatIdC.value_as_string).to_string()
                     )

        cidrList = [
            "10.10.88.0/23",
            "10.10.100.0/24",
            "10.10.136.0/22",
            "10.10.160.0/21",
            "10.40.0.0/16",
            "10.205.0.0/16",
            "172.18.0.0/16",
            "172.19.0.0/16",
            "172.20.0.0/16",
            "172.28.0.0/16",
            "172.29.0.0/16",
            "172.21.0.0/16"
        ]

        self.routeTgw("PrivateRouteAToTGW", rtA.ref, existTgw.value_as_string, cidrList, isTgw.logical_id)
        #self.routeTgw("PrivateRouteCToTGW", rtC.ref, existTgw.value_as_string, cidrList, isTgw.logical_id)
        self.routeTgw("PrivateRouteBToTGW", rtB.ref, existTgw.value_as_string, cidrList, isTgw.logical_id)
        self.routeTgw("PrivateRouteDBAToTGW", rtDBA.ref, existTgw.value_as_string, cidrList, isTgw.logical_id)
        #self.routeTgw("PrivateRouteDBCToTGW", rtDBC.ref, existTgw.value_as_string, cidrList, isTgw.logical_id)
        self.routeTgw("PrivateRouteDBBToTGW", rtDBB.ref, existTgw.value_as_string, cidrList, isTgw.logical_id)

        addRoutelambdaRole = iam.CfnRole(
            self,
            "addRouteLambdaRole",
            # role_name="addRouteLambdaRole",
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
                "policyName" : "addRouteLambdaPolicy",
                "policyDocument" : {
                "Version":"2012-10-17",
                "Statement" : [
                {
                  "Effect": "Allow",
                  "Action" : [
                    "ec2:Describe*",
                    "ec2:CreateTags",
                    "ec2:CreateRoute",
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

        addRoutelambda_layer = _lambda.CfnLayerVersion(
            self,
            "addRoutelambda_layer",
            layer_name="addRoutelambda-layer",
            compatible_runtimes=['python3.6', 'python3.7', 'python3.8'],
            content=_lambda.CfnLayerVersion.ContentProperty(
                s3_bucket=UPLOAD_BUCKET,
                s3_key="requests_pack.zip"
            ),
            description="addRoutelambda layer",
            license_info="MIT"
        )

        addRoutelambdafunction = _lambda.CfnFunction(
            self,
            "addRouteFunction",
            runtime="python3.7",
            timeout = 120,
            handler="addRoute.handler",
            code=_lambda.CfnFunction.CodeProperty(
                s3_bucket=UPLOAD_BUCKET,
                s3_key="addRoute.zip"
            ),
            layers=[addRoutelambda_layer.ref],
            role=addRoutelambdaRole.attr_arn,
            environment = {
                "variables" : {
                    "envName" : envName.value_as_string,
                    "PrivateWebSubnetA" : PrivateWebSubnetA.ref,
                    "PrivateWebSubnetB" : PrivateWebSubnetB.ref,
                    "PrivateDbSubnetA" : PrivateDbSubnetA.ref,
                    "PrivateDbSubnetB" : PrivateDbSubnetB.ref,
                    "tgwid" : existTgw.value_as_string
                }
            }
        )
        addRoutelambdafunction.add_depends_on(addRoutelambdaRole)

        # cfn.CfnCustomResource(
        #     self,
        #     "CallAccountRoute",
        #     service_token=addRoutelambdafunction.attr_arn
        # )

        core.CustomResource(
            self,
            "CallAccountRoute",
            resource_type="Custom::CallAccountRoute",
            service_token=addRoutelambdafunction.attr_arn
        )

        shareRes = ram.CfnResourceShare(self,
                                        id="SubnetShare",
                                        name="RAM-Subnet-" + appName.value_as_string + "-" + envName.value_as_string,
                                        principals=[sharedAccountId.value_as_string],
                                        resource_arns=[
                                            "arn:aws:ec2:" + self.region + ":" + self.account + ":subnet/" + PrivateWebSubnetA.ref,
                                            #"arn:aws:ec2:" + self.region + ":" + self.account + ":subnet/" + PrivateWebSubnetC.ref,
                                            "arn:aws:ec2:" + self.region + ":" + self.account + ":subnet/" + PrivateWebSubnetB.ref,
                                            "arn:aws:ec2:" + self.region + ":" + self.account + ":subnet/" + PrivateDbSubnetA.ref,
                                            #"arn:aws:ec2:" + self.region + ":" + self.account + ":subnet/" + PrivateDbSubnetC.ref,
                                            "arn:aws:ec2:" + self.region + ":" + self.account + ":subnet/" + PrivateDbSubnetB.ref
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
            #PrivateWebSubnetC.ref
            PrivateWebSubnetB.ref
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
  "Action":["s3:GetObject*","s3:ListAllMyBuckets","s3:ListObject*","s3:PutObject*","s3:List*"],
  "Resource":["arn:aws:s3:::*","arn:aws:s3:::*/*"]
}]
}
      """
        epS3 = ec2.CfnVPCEndpoint(self,
                                  id="EndportS3",
                                  service_name="com.amazonaws." + REGION.SEOUL + ".s3",
                                  vpc_id=vpcId.value_as_string,
                                  route_table_ids=[
                                      rtA.ref,
                                      rtB.ref
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
                                               id="VPCEPrivateSubnetSecurityGroup",
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

    def NetworkAcl(self, key, vpc):
        return ec2.CfnNetworkAcl(self,
                                 id=key,
                                 vpc_id=vpc
                                 )

    def NAclAssociation(self, key, subnetId, NAclId):
        return ec2.CfnSubnetNetworkAclAssociation(self,
                                                  id=key,
                                                  subnet_id=subnetId,
                                                  network_acl_id=NAclId
                                                  )
    def NetworkAclEntry(self, key, NAclId, egbool):
        return ec2.CfnNetworkAclEntry(self,
                                      id=key,
                                      network_acl_id=NAclId,
                                      protocol=-1,
                                      rule_action="allow",
                                      rule_number=100,
                                      egress=egbool,
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
