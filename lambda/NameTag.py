#!/usr/bin/env python3
import boto3
import os
import re
import json
import time
import requests
import logging
import sys

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

def handler(event, context):
    try:
        ssm = boto3.client('ssm')
        ec2 = boto3.client('ec2')
        responseStatus = 'SUCCESS'
        responseData = {}
        
        #get parameter store
        vpcId = ssm.get_parameter(Name='vpcId')
        privateWebSubnetACidr = ssm.get_parameter(Name='privateWebSubnetACidr')
        privateWebSubnetBCidr = ssm.get_parameter(Name='privateWebSubnetBCidr')
        privateDbSubnetACidr = ssm.get_parameter(Name='privateDbSubnetACidr')
        privateDbSubnetBCidr = ssm.get_parameter(Name='privateDbSubnetBCidr')
        publicSubnetAId = ssm.get_parameter(Name='publicSubnetAId')
        publicSubnetBId = ssm.get_parameter(Name='publicSubnetBId')
        envName = ssm.get_parameter(Name='envName')
        #get lambda environment
        netAclDB_tags = os.environ['netAclDB_tags']
        netAclWeb_tags = os.environ['netAclWeb_tags']
        netAclPublic_tags = os.environ['netAclPublic_tags']
        privateDbSubnetA_tags = os.environ['privateDbSubnetA_tags']
        privateDbSubnetB_tags = os.environ['privateDbSubnetB_tags']
        privateWebSubnetA_tags = os.environ['privateWebSubnetA_tags']
        privateWebSubnetB_tags = os.environ['privateWebSubnetB_tags']
        rtDBA_tags = os.environ['rtDBA_tags']
        rtDBB_tags = os.environ['rtDBB_tags']
        rtWebA_tags	= os.environ['rtWebA_tags']
        rtWebB_tags = os.environ['rtWebB_tags']

        if envName['Parameter']['Value'] == 'dev':
            rtPub_tags = "RT-dev-PUB-mgmt"
            vpc_tags = "dev-VPC"
            igw_tags = "dev-IGW"
            publicSubnetA_tags = "dev-public-mgmt-128-a"
            publicSubnetC_tags = "dev-public-mgmt-129-c"
            publicSubnetB_tags = "dev-public-mgmt-130-b"
            putParam("subnet-0b0a8400e376270a2", "dev-public-mgmt-129-c")
        else:
            rtPub_tags = "RT-prod-PUB-mgmt"
            vpc_tags = "prod-VPC"
            igw_tags = "prod-IGW"
            publicSubnetA_tags = "prod-public-mgmt-0-a"
            publicSubnetC_tags = "prod-public-mgmt-1-c"    
            publicSubnetB_tags = "prod-public-mgmt-2-b"
            putParam("subnet-0288f165bc13d9d56", "prod-public-mgmt-1-c")            

        subnet_info = {privateWebSubnetACidr['Parameter']['Value'] : privateWebSubnetA_tags,
                    privateWebSubnetBCidr['Parameter']['Value'] : privateWebSubnetB_tags,
                    privateDbSubnetACidr['Parameter']['Value'] : privateDbSubnetA_tags,
                    privateDbSubnetBCidr['Parameter']['Value'] : privateDbSubnetB_tags,
                    publicSubnetAId['Parameter']['Value'] : publicSubnetA_tags, 
                    publicSubnetBId['Parameter']['Value'] : publicSubnetB_tags}

        vpcs = ec2.describe_vpcs()['Vpcs']
        for vpc in vpcs:
            if vpc['VpcId'] == vpcId['Parameter']['Value']:
                tag_result = findTags(vpc)
                if tag_result == "notfound":
                    ec2.create_tags(Resources=[vpc['VpcId']], Tags=[{'Key': 'Name', 'Value': vpc_tags}])

        subnets = ec2.describe_subnets(Filters=[{'Name': 'vpc-id', 'Values': [vpcId['Parameter']['Value']]}])
        ## waiting for create subnet
        i = 0
        cnt = 0
        while True:
            if len(subnets['Subnets']) >= 6:
                break
            else:
                cnt += 1
                time.sleep(5)
            if cnt > 30:
                break
        ## - end

        for s_info in subnet_info.keys():
            for subnet in subnets['Subnets']:
                if subnet['SubnetId'] == s_info:
                    putParam(subnet['SubnetId'], subnet_info[s_info])
                    tag_result = findTags(subnet)
                    if tag_result == "notfound":
                        ec2.create_tags(Resources=[subnet['SubnetId']], Tags=[{'Key': 'Name', 'Value': subnet_info[s_info]}])
                elif subnet['CidrBlock'] == s_info:
                    putParam(subnet['SubnetId'], subnet_info[s_info])
                    tag_result = findTags(subnet)
                    if tag_result == "notfound":
                        ec2.create_tags(Resources=[subnet['SubnetId']], Tags=[{'Key': 'Name', 'Value': subnet_info[s_info]}])

        routes = ec2.describe_route_tables()
        for route in routes['RouteTables']:
            for route_sub in route['Associations']:
                if 'SubnetId' in route_sub.keys():
                    tag_result = findTags(route)
                    if tag_result == "notfound":
                        get_param_route = ssm.get_parameter(Name=route_sub['SubnetId'])['Parameter']['Value']
                        if re.search('-web-[A-a0-9]*-a$', get_param_route):
                            ec2.create_tags(Resources=[route_sub['RouteTableId']], Tags=[{'Key': 'Name', 'Value': rtWebA_tags}])
                        elif re.search('-web-[A-a0-9]*-b$', get_param_route):
                            ec2.create_tags(Resources=[route_sub['RouteTableId']], Tags=[{'Key': 'Name', 'Value': rtWebB_tags}])
                        elif re.search('-db-[A-a0-9]*-a$', get_param_route):
                            ec2.create_tags(Resources=[route_sub['RouteTableId']], Tags=[{'Key': 'Name', 'Value': rtDBA_tags}])
                        elif re.search('-db-[A-a0-9]*-b$', get_param_route):
                            ec2.create_tags(Resources=[route_sub['RouteTableId']], Tags=[{'Key': 'Name', 'Value': rtDBB_tags}])
                        elif re.search(publicSubnetA_tags, get_param_route):
                            ec2.create_tags(Resources=[route_sub['RouteTableId']], Tags=[{'Key': 'Name', 'Value': rtPub_tags}])

        nacls = ec2.describe_network_acls()
        for nacl in nacls['NetworkAcls']:
            for nacl_entries in nacl['Entries']:
                tag_result = findTags(nacl_entries)
                if tag_result == "notfound":
                    for nacl_id in nacl['Associations']:
                        if re.search('-db-', ssm.get_parameter(Name=nacl_id['SubnetId'])['Parameter']['Value']):
                            ec2.create_tags(Resources=[nacl_id['NetworkAclId']], Tags=[{'Key': 'Name', 'Value': netAclDB_tags}])
                        elif re.search('-web-', ssm.get_parameter(Name=nacl_id['SubnetId'])['Parameter']['Value']):
                            ec2.create_tags(Resources=[nacl_id['NetworkAclId']], Tags=[{'Key': 'Name', 'Value': netAclWeb_tags}])
                        elif re.search('-public-', ssm.get_parameter(Name=nacl_id['SubnetId'])['Parameter']['Value']):
                            ec2.create_tags(Resources=[nacl_id['NetworkAclId']], Tags=[{'Key': 'Name', 'Value': netAclPublic_tags}])

        igws = ec2.describe_internet_gateways()
        for igw in igws['InternetGateways']:
            if igw['Attachments'][0]['VpcId'] == vpcId['Parameter']['Value']:
                tag_result = findTags(igw)
                if tag_result == "notfound":
                    ec2.create_tags(Resources=[igw['InternetGatewayId']], Tags=[{'Key': 'Name', 'Value': igw_tags}])

    #        print(response)
        responseData = {'Success': 'Tags Created.'}
        sendResponse(event, context, responseStatus, responseData)       
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        responseStatus = 'FAILED'
        responseData = {'Failed': 'Failed to Tags Created.'}
        sendResponse(event, context, responseStatus, responseData) 

def sendResponse(event, context, responseStatus, responseData):
    responseBody = {'Status': responseStatus,
                    'Reason': 'See the details in CloudWatch Log Stream: ' + context.log_stream_name,
                    'PhysicalResourceId': context.log_stream_name,
                    'StackId': event['StackId'],
                    'RequestId': event['RequestId'],
                    'LogicalResourceId': event['LogicalResourceId'],
                    'Data': responseData}
    LOGGER.info('RESPONSE BODY:n' + json.dumps(responseBody))
    try:
        req = requests.put(event['ResponseURL'], data=json.dumps(responseBody))
        if req.status_code != 200:
            LOGGER.info(req.text)
            raise Exception('Recieved non 200 response while sending response to CFN.')
        return
    except requests.exceptions.RequestException as e:
        LOGGER.error(e)
        raise

def findTags(n_data):
    if 'Tags' in n_data.keys():
        for tag in n_data['Tags']:
            if tag['Key'] == 'Name':
                return "found"
    return "notfound"

def putParam(p_name, p_value, p_type='String'):
    ssm = boto3.client('ssm')
    return ssm.put_parameter(Name=p_name, Value=p_value, Type=p_type, Overwrite=True)

# if __name__ == '__main__':
#    handler('event', 'handler')