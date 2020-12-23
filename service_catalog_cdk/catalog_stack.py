from aws_cdk import (
    aws_servicecatalog as sc,
    aws_ssm as ssm,
    aws_iam as iam,
    core
)

from common.var import *

PRODUCT_NETWORK_URL = URL_PRODUCTS.VPC
PRODUCT_NETWORK_SUBNET_URL = URL_PRODUCTS.SUBNET

ASSUMED_SSO_MASTER_ROLE = ""
PF_VERSION = "v0.1.x"
VPC_PRD_VER = "v0.0.2"
SUBNET_PRD_VER = "v0.0.5"


class CatalogStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # The code that defines your stack goes here

        provider_name = "11st System Engineering Team"

        # ssmLoadTemplateFromURL = ssm.StringParameter.value_for_string_parameter(
        #     self, "s3-product"
        # )

        networkPortfolio = sc.CfnPortfolio(
            self,
            id="network-portfolio",
            display_name="11st Network Portfolio - VPC related",
            provider_name=provider_name,
            description="11st Network Portfolio - VPC related"
        )

        ###############
        # VPC product
        ###############
        vpcProduct = sc.CfnCloudFormationProduct(
            self,
            id="vpc-product",
            name="vpc-product",
            owner=provider_name,
            description="network product - VPC, subnet, NAT, IGW, TGW",
            provisioning_artifact_parameters=[

                sc.CfnCloudFormationProduct.ProvisioningArtifactPropertiesProperty(
                    info=core.Token.as_any({
                        "LoadTemplateFromURL": PRODUCT_NETWORK_URL
                    }),
                    name="vpc-" + PF_VERSION + "-" + VPC_PRD_VER
                ),
            ]
        )

        vpcAssociation = sc.CfnPortfolioProductAssociation(
            self,
            id="network-association",
            portfolio_id=networkPortfolio.ref,
            product_id=vpcProduct.ref
        )

        vpcAssociation.add_depends_on(networkPortfolio)
        vpcAssociation.add_depends_on(vpcProduct)

        ssmParamRole = ssm.StringParameter.value_for_string_parameter(
            self, "/org/primary/service_catalog/constraint/role_arn"
        )

        vpcConstraint = sc.CfnLaunchRoleConstraint(
            self,
            id="network-constraint",
            portfolio_id=networkPortfolio.ref,
            product_id=vpcProduct.ref,
            role_arn=ssmParamRole
        )

        vpcConstraint.add_depends_on(networkPortfolio)
        vpcConstraint.add_depends_on(vpcProduct)
        vpcConstraint.add_depends_on(vpcAssociation)

        role = iam.Role.from_role_arn(
            self,
            id="Role",
            role_arn=ASSUMED_SSO_MASTER_ROLE
        )

        sc.CfnPortfolioPrincipalAssociation(
            self,
            id="principal-role",
            portfolio_id=networkPortfolio.ref,
            principal_arn=role.role_arn,
            principal_type="IAM"
        )

        ###############
        # Subnet product
        ###############
        subnetProduct = sc.CfnCloudFormationProduct(
            self,
            id="subnet-product",
            name="subnet-product",
            owner=provider_name,
            description="Subnet product - private subnet, NAT",
            provisioning_artifact_parameters=[

                sc.CfnCloudFormationProduct.ProvisioningArtifactPropertiesProperty(
                    info=core.Token.as_any({
                        "LoadTemplateFromURL": PRODUCT_NETWORK_SUBNET_URL
                    }),
                    name="subnet-" + PF_VERSION + "-" + SUBNET_PRD_VER
                ),
            ]
        )

        subnetAssociation = sc.CfnPortfolioProductAssociation(
            self,
            id="subnet-association",
            portfolio_id=networkPortfolio.ref,
            product_id=subnetProduct.ref
        )

        subnetAssociation.add_depends_on(networkPortfolio)
        subnetAssociation.add_depends_on(subnetProduct)

        # ssmParamRole = ssm.StringParameter.value_for_string_parameter(
        #     self, "/org/primary/service_catalog/constraint/role_arn"
        # )

        subnetConstraint = sc.CfnLaunchRoleConstraint(
            self,
            id="subnet-constraint",
            portfolio_id=networkPortfolio.ref,
            product_id=subnetProduct.ref,
            role_arn=ssmParamRole
        )

        subnetConstraint.add_depends_on(networkPortfolio)
        subnetConstraint.add_depends_on(subnetProduct)
        subnetConstraint.add_depends_on(subnetAssociation)

        ## 거버넌스랑 붙게 될 예정
        #### Tagging
        myTags = {
            "Team": "Cloud Engineering Team",
            "Environment": "prod/dev"
        }

        myTags["EmpNo"] = "1101167"
        myTags["Project"] = "Landing Zone CDK"

        for key in myTags:
            val = myTags[key]
            core.Tag.add(networkPortfolio, key, val)
            core.Tag.add(vpcProduct, key, val)
            core.Tag.add(subnetProduct, key, val)
