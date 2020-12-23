#!/usr/bin/env python3
### click options ref : https://click.palletsprojects.com/en/7.x/options/
import json
import os

import boto3
import sys

# export PYTHONPATH="$PYTHONPATH:{common.var.py's path}"
from common.var import *

import yaml
import click
from pyfzf.pyfzf import FzfPrompt

fzf = FzfPrompt()


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def set_kv(**kwargs):
    ret = {}
    for key, value in kwargs.items():
        ret['Key'] = key
        ret['Value'] = value

    return ret


def set_parameter(params, is_update=False):
    ret = [
        # set_kv(AccountId=ACCOUNT.SHARED),
        set_kv(Region="ap-northeast-2"),
        set_kv(StackSetName="devEventPrivateSubnet")
    ]
    for item, doc in params.items():
        # if "Default" not in doc:
        #     continue

        if is_update:
            dic = {'Key': item,
                   'Value': doc["Default"],
                   'UsePreviousValue': is_update
                   }
        else:
            dic = {'Key': item,
                   'Value': doc["Default"]
                   }
        ret.append(dic)

    return ret


def read_parameter_from_file(file):
    with open(file, 'r') as fileData:
        try:
            data = yaml.safe_load(fileData)
            for item, doc in data.items():
                print(item, ":", doc)

        except yaml.YAMLError as e:
            print(e)

    return data


def get_portfolio_list(sc):
    result_pf = sc.list_portfolios()
    result_imp_pf = sc.list_accepted_portfolio_shares(
        PortfolioShareType='IMPORTED'
    )
    list_pf = []
    for pf in result_pf["PortfolioDetails"] + result_imp_pf["PortfolioDetails"]:
        list_pf.append({"Id": pf["Id"], "DisplayName": pf["DisplayName"]})

    return list_pf


def get_product_list(sc, portfolio_id):
    result_pp = sc.search_products_as_admin(
        PortfolioId=portfolio_id
    )
    list_pp = []
    for pp in result_pp["ProductViewDetails"]:
        list_pp.append({"Id": pp["ProductViewSummary"]["ProductId"], "Name": pp["ProductViewSummary"]["Name"]})

    return list_pp


def get_artifact_list(sc, product_id):
    result_pa = sc.list_provisioning_artifacts(
        ProductId=product_id
    )

    list_pa = []
    for pa in result_pa["ProvisioningArtifactDetails"]:
        list_pa.append({"Id": pa["Id"], "Name": pa["Name"], "Desc": pa.get("Description", "No Desc")})

    return list_pa


def get_parameter_file_list():
    list = []
    var_params = PARAMETER()
    for param in dir(var_params):
        if not callable(getattr(var_params, param)) and not param.startswith("__"):
            list.append({"key": param, "value": getattr(var_params, param)})
    return list


def read_fzf(list, header):
    opt = f'--reverse --cycle --header "{header}"'

    select = fzf.prompt(list, fzf_options=opt)[0]
    print(f'Selected : {select}')
    try:
        return json.loads(select.replace("'", "\""))
    except ValueError as e:
        return select


def product_id_fzf(sc):
    list_pf = get_portfolio_list(sc)
    selected_pf = read_fzf(list_pf, "Select Portfolio")

    list_pp = get_product_list(sc, selected_pf["Id"])
    selected_pp = read_fzf(list_pp, "Select Product")
    return selected_pp["Id"]


def artifact_id_fzf(sc, product_id):
    list_pa = get_artifact_list(sc, product_id)
    selected_pa = read_fzf(list_pa, "Select Product Artifact")
    return selected_pa["Id"]


def parameters_fzf():
    list_param = get_parameter_file_list()
    selected_param = read_fzf(list_param, "Select Parameter file")
    return read_parameter_from_file("../" + selected_param['value'])


def get_list(sc, arg):
    if arg == 'provisioned' or arg == 'p':
        result = sc.search_provisioned_products(
            AccessLevelFilter={
                'Key': 'User',  # 'Account' | 'Role' | 'User'
                'Value': 'self'
            }
        )

        print(f'Provisioned Products')
        for prod in result['ProvisionedProducts']:
            print(f'{prod["Status"]} - {prod["Name"]}')
        pass
    elif arg == 'all' or arg == 'a':
        result = sc.list_portfolios()
        for pf in result["PortfolioDetails"]:
            print(f'{pf["Id"]} - {pf["DisplayName"]}')
            result_pp = sc.search_products_as_admin(
                PortfolioId=pf["Id"]
            )
            for pp in result_pp["ProductViewDetails"]:
                print(f'\t{pp["ProductViewSummary"]["ProductId"]} - {pp["ProductViewSummary"]["Name"]}')
                result_pa = sc.list_provisioning_artifacts(
                    ProductId=pp["ProductViewSummary"]["ProductId"]
                )
                for pa in result_pa["ProvisioningArtifactDetails"]:
                    print(f'\t\t{pa["Id"]} - {pa["Name"]} - {pa.get("Description", "No Desc")}')

        pass
    elif arg == 'portfolio' or arg == 'pf':
        list_pf = sc.list_portfolios()
        result_imp_pf = sc.list_accepted_portfolio_shares(
            PortfolioShareType='IMPORTED'
        )
        print('Portfolio list - LOCAL')
        for pf in list_pf["PortfolioDetails"]:
            print(f'{pf["Id"]} - {pf["DisplayName"]}')
        if bool(result_imp_pf["PortfolioDetails"]):
            print('\nPortfolio list - IMPORTED')
            for pf in result_imp_pf["PortfolioDetails"]:
                print(f'{pf["Id"]} - {pf["DisplayName"]}')
        pass
    elif 'port-' in arg:
        result = sc.search_products_as_admin(
            PortfolioId=arg
        )
        for pp in result["ProductViewDetails"]:
            print(f'{pp["ProductViewSummary"]["ProductId"]} - {pp["ProductViewSummary"]["Name"]}')
        pass
    elif 'prod-' in arg:
        result_pa = sc.list_provisioning_artifacts(
            ProductId=arg
        )
        for pa in result_pa["ProvisioningArtifactDetails"]:
            print(f'{pa["Id"]} - {pa["Name"]} - {pa.get("Description", "No Desc")}')
        pass
    else:
        print(f'list available args : p, a, pf, port-xxx, prod-xxx')
    pass


########################################################################

@click.command()
@click.option('-p', '--profile', help='aws profile')
@click.option('-ch', '--check-pipeline', is_flag=True, help='provisioned product list')
@click.option('-l', '--list', is_flag=True, help='provisioned(p)')
@click.option('-ll', '--list-list', help='provisioned(p) | all(a) | portfolio(pf) | port-xxxxx | prod-xxxxx')
# @click.option('-pid', '--product-id', help='product id for create.')
# @click.option('-aid', '--artifact-id', help='artifact id for create.')
@click.option('-c', '--create', is_flag=True, help='create aws resource.')
@click.option('-ce', '--create-explicit', help='create Explicit aws resource.')
@click.option('-u', '--update', is_flag=True, help='update privisioned aws resource.')
@click.option('-d', '--delete', is_flag=True, help='delete aws resource.')
@click.option('-de', '--delete-explicit', help='delete Explicit provisioned name.')
@click.option('-f', '--file', help='parameter file (yaml)')
@click.option('-n', '--name', default='default-private-subnet', help='provisioning name.', show_default=True)
@click.option('-s', '--start', default=0, help='start of range', show_default=True)
@click.option('-e', '--end', default=1, help='end of range', show_default=True)
def main(profile,
         check_pipeline, list, list_list,
         # product_id, artifact_id,
         create, create_explicit, update, delete, delete_explicit,
         file,
         name, start, end):

    if profile is not None:
        session = boto3.Session(profile_name=profile)
    else:
        session = boto3.Session(profile_name='default')
    sc = session.client('servicecatalog')
    """ :type: pyboto3.servicecatalog """

    pipe = session.client('codepipeline')
    """ :type: pyboto3.codepipeline """

    params = None

    if file is not None:
        params = read_parameter_from_file(file)

    if check_pipeline:
        pip_state = pipe.get_pipeline_state(
            name="service-catalog-cdk"
        )
        for state in pip_state['stageStates']:
            for action in state['actionStates']:
                print(
                    f'{action["actionName"]} - {action["latestExecution"]["status"]} - {action["latestExecution"].get("externalExecutionUrl", "")}')

    if list_list is not None:
        get_list(sc, list_list)

    if list:
        get_list(sc, 'p')
        pass
    elif create:
        product_id = product_id_fzf(sc)
        artifact_id = artifact_id_fzf(sc, product_id)
        if params is None:
            params = parameters_fzf()

        for i in range(start, end):
            sc.provision_product(
                AcceptLanguage='en',
                ProductId=product_id,
                ProvisioningArtifactId=artifact_id,
                ProvisionedProductName=name + "-" + str(i),
                ProvisioningParameters=set_parameter(params)
            )
        pass
    elif create_explicit:
        product_id = product_id_fzf(sc)
        artifact_id = artifact_id_fzf(sc, product_id)
        if params is None:
            params = parameters_fzf()

        for i in range(start, end):
            sc.provision_product(
                AcceptLanguage='en',
                ProductId=product_id,
                ProvisioningArtifactId=artifact_id,
                ProvisionedProductName=create_explicit,
                ProvisioningParameters=set_parameter(params)
            )
        pass
    elif update:
        product_id = product_id_fzf(sc)
        artifact_id = artifact_id_fzf(sc, product_id)
        if params is None:
            params = parameters_fzf()

        sc.update_provisioned_product(
            AcceptLanguage='en',
            ProductId=product_id,
            ProvisioningArtifactId=artifact_id,
            ProvisionedProductName=name,
            ProvisioningParameters=set_parameter(params, False)
        )
        pass
    elif delete:
        for i in range(start, end):
            sc.terminate_provisioned_product(
                ProvisionedProductName=name + "-" + str(i)
            )
        pass
    elif delete_explicit is not None:
        sc.terminate_provisioned_product(
            ProvisionedProductName=delete_explicit
        )
        pass


if __name__ == '__main__':
    if sys.argv.__len__() < 2:
        print(f'{os.path.basename(__file__)} --help')
    else:
        sys.exit(main())
