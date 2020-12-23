#!/usr/bin/env python3

from aws_cdk import core

from service_catalog_cdk.catalog_stack import CatalogStack
from products.subnet_product import SubnetProductStack
from products.vpc_product import VpcProductStack
from service_catalog_cdk.service_catalog_cdk_stack import ServiceCatalogCdkStack
from stacksets.subnet_stackset import SubnetStacksetStack
from stacksets.subnet_nametag_stackset import SubnetNameTagStacksetStack
from stacksets.vpc_stackset import VpcStacksetStack
#from service_catalog_cdk.catalog_stack_instance import CatalogInstanceStack
#from products.instance_product import InstanceProductStack
#from stacksets.instance_stackset import InstanceStacksetStack

app = core.App()
# ServiceCatalogCdkStack(app, "service-catalog-cdk")

CatalogStack(app, "catalog")
#VpcProductStack(app, "vpc-product")
#VpcStacksetStack(app, "vpc-stackset")

#instanceProp = app.node.try_get_context('instance')
#InstanceProductStack(app, "instance-product", props=instanceProp)
#InstanceStacksetStack(app, "instance-stackset", props=instanceProp)

subnetProp = app.node.try_get_context('subnet')
SubnetProductStack(app, "subnet-product", props=subnetProp)
SubnetStacksetStack(app, "subnet-stackset", props=subnetProp)
SubnetNameTagStacksetStack(app, "subnet-nametag-stackset", props=subnetProp)

app.synth()
