#!/usr/bin/env python3
import datetime

import boto3
import sys
import getopt

import json
import yaml

from common.var import *

###### Const Variable

PRODUCT_ID = ""

TGW_ID = ""

VPC_ID = ""
PUBLIC_SUBNET_ID1 = ""
PUBLIC_SUBNET_ID2 = ""

NAT_ID1 = ""
NAT_ID2 = ""

PRIVATE_SUBNET_WEB1_CIDR = "10.192.130.0/24"
PRIVATE_SUBNET_WEB2_CIDR = "10.192.131.0/24"
PRIVATE_SUBNET_DB1_CIDR = "10.192.132.0/24"
PRIVATE_SUBNET_DB2_CIDR = "10.192.133.0/24"

# PARAMETER_PROD_FILE = PARAMETER.SUBNET_PROD_DEVVPC
# PARAMETER_PROD_FILE = PARAMETER.SUBNET_PROD_PRODVPC

def print_dict_to_json(input={}):
    print(json.dumps(input, indent=4, default=str))

def setParam(**kwargs):
    ret = {}
    for key, value in kwargs.items():
        ret['Key'] = key
        ret['Value'] = value

    return ret


def paramProd(env):
    if env in "dev":
        PARAMETER_PROD_FILE = PARAMETER.SUBNET_PROD_DEVVPC
    else:
        PARAMETER_PROD_FILE = PARAMETER.SUBNET_PROD_PRODVPC

    with open(PARAMETER_PROD_FILE, 'r') as stream:
        try:
            params = yaml.safe_load(stream)

        except yaml.YAMLError as e:
            print(e)

    ret = []
    ret.append(setParam(AccountId=ACCOUNT.SHARED))
    ret.append(setParam(Region="ap-northeast-2"))
    ret.append(setParam(StackSetName="devEventPrivateSubnet"))
    for item, doc in params.items():
        dic = {}
        dic['Key'] = item
        dic['Value'] = doc["Default"]

        ret.append(dic)
    return ret




def main(argv):
    sc = boto3.client('servicecatalog')
    """ :type: pyboto3.servicecatalog """

    try:
        opts, etc_args = getopt.getopt(argv[1:], \
                                       "hd:c:u:lw", ["help", "delete=", "create=", "update=", "list", "watch"])
    except getopt.GetoptError:
        print(f'{argv[0]} -h')
        sys.exit(2)

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(f'{argv[0]} -l : list')
            print(f'{argv[0]} -c name : create product')
            print(f'{argv[0]} -d name : delete product')
            sys.exit()
        elif opt in ("-w", "--watch"):

            cfn = boto3.client('cloudformation')
            """ :type: pyboto3.cloudformation """

            retcfn = cfn.describe_stacks(StackName="catalog")

            result = sc.describe_product_as_admin(
                Id="prod-uofzw35ch3yee"
            )
            print(f'{retcfn["Stacks"][0]["StackStatus"]} - {result["ProvisioningArtifactSummaries"][0]["Name"]}')
        elif opt in ("-d", "--delete"):
            sc.terminate_provisioned_product(
                ProvisionedProductName=arg
            )
        elif opt in ("-u", "--update"):
            result = sc.list_provisioning_artifacts(
                ProductId=PRODUCT_ID
            )

            sc.update_provisioned_product(
                AcceptLanguage='en',
                ProvisionedProductName=arg,
                ProvisionedProductId=PRODUCT_ID,
                ProductId=PRODUCT_ID,
                ProvisioningParameters=paramProd()

            )


        elif opt in ("-c", "--create"):

            result = sc.list_provisioning_artifacts(
                ProductId=PRODUCT_ID
            )

            if arg in "dev" :
                sc.provision_product(
                    AcceptLanguage='en',
                    ProductId=PRODUCT_ID,
                    ProvisioningArtifactId=result['ProvisioningArtifactDetails'][0]['Id'],
                    ProvisionedProductName="dev-event-subnet",
                    ProvisioningParameters=paramProd(arg)
                )
            else:
                sc.provision_product(
                    AcceptLanguage='en',
                    ProductId=PRODUCT_ID,
                    ProvisioningArtifactId=result['ProvisioningArtifactDetails'][0]['Id'],
                    ProvisionedProductName="prod-event-subnet",
                    ProvisioningParameters=paramProd(arg)
                )
        elif opt in ("-l", "--list"):
            result = sc.search_provisioned_products(
                AccessLevelFilter={
                    'Key': 'User',  # 'Account' | 'Role' | 'User'
                    'Value': 'self'
                }
            )

            for prod in result['ProvisionedProducts']:
                print(f'{prod["Status"]} - {prod["Name"]}')


if __name__ == '__main__':
    sys.exit(main(sys.argv))
