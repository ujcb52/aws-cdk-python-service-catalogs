from aws_cdk import (
    aws_servicecatalog as sc,
    aws_ssm as ssm,
    aws_iam as iam,
    core
)

from common.var import *

PRODUCT_INSTANCE_EC2_URL = URL_PRODUCTS.INSTANCE

ASSUMED_SSO_MASTER_ROLE = ""
PF_VERSION = "v0.1.x"
VPC_PRD_VER = "v0.0.1"
INSTANCE_PRD_VER = "v0.0.1"


class CatalogInstanceStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # The code that defines your stack goes here

        provider_name = "11st System Engineering Team"

        # ssmLoadTemplateFromURL = ssm.StringParameter.value_for_string_parameter(
        #     self, "s3-product"
        # )

        instancePortfolio = sc.CfnPortfolio(
            self,
            id="instance-portfolio",
            display_name="11st instance Portfolio - EC2",
            provider_name=provider_name,
            description="11st instance Portfolio - EC2"
        )

        ###############
        # EC2 product
        ###############
        instancePortfolio = sc.CfnCloudFormationProduct(
            self,
            id="instance-product",
            name="instance-product",
            owner=provider_name,
            description="Instance product - EC2",
            provisioning_artifact_parameters=[

                sc.CfnCloudFormationProduct.ProvisioningArtifactPropertiesProperty(
                    info=core.Token.as_any({
                        "LoadTemplateFromURL": PRODUCT_INSTANCE_EC2_URL
                    }),
                    name="instance-" + PF_VERSION + "-" + INSTANCE_PRD_VER
                ),
            ]
        )

        instanceAssociation = sc.CfnPortfolioProductAssociation(
            self,
            id="instance-association",
            portfolio_id=instancePortfolio.ref,
            product_id=instancePortfolio.ref
        )

        instanceAssociation.add_depends_on(instancePortfolio)
        instanceAssociation.add_depends_on(instancePortfolio)

        ssmParamRole = ssm.StringParameter.value_for_string_parameter(
            self, "/org/primary/service_catalog/constraint/role_arn"
        )

        instanceConstraint = sc.CfnLaunchRoleConstraint(
            self,
            id="instance-constraint",
            portfolio_id=instancePortfolio.ref,
            product_id=instancePortfolio.ref,
            role_arn=ssmParamRole
        )

        instanceConstraint.add_depends_on(instancePortfolio)
        instanceConstraint.add_depends_on(instancePortfolio)
        instanceConstraint.add_depends_on(instanceAssociation)

        ## 거버넌스랑 붙게 될 예정
        #### Tagging
        myTags = {
            "Team": "System Engineering Team",
            "Environment": "prod/dev"
        }

        myTags["EmpNo"] = "1101167"
        myTags["Project"] = "Landing Zone CDK"

        for key in myTags:
            val = myTags[key]
            core.Tag.add(instancePortfolio, key, val)
