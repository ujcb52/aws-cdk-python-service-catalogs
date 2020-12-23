#!/usr/bin/env python3
import boto3
import os
import json
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

        envName = os.environ['envName']
        PrivateWebSubnetA = os.environ['PrivateWebSubnetA']
        PrivateWebSubnetB = os.environ['PrivateWebSubnetB']
        PrivateDbSubnetA = os.environ['PrivateDbSubnetA']
        PrivateDbSubnetB = os.environ['PrivateDbSubnetB']
        PrivateDbSubnetB = os.environ['PrivateDbSubnetB']
        tgwid = os.environ['tgwid']

        # envName = "dev"
        # PrivateWebSubnetA = "subnet-027608b42d1db3c1b"
        # PrivateWebSubnetB = ""
        # PrivateDbSubnetA = ""
        # PrivateDbSubnetB = ""
        # tgwid = ""

        cidrList = ['10.192.0.0/23']
        subnet_info = [PrivateWebSubnetA, PrivateWebSubnetB,
                       PrivateDbSubnetA, PrivateDbSubnetB]

        if envName == 'dev':
            routes = ec2.describe_route_tables()
            for route in routes['RouteTables']:
                for route_sub in route['Associations']:
                    if check_helper(route['Routes'], route_sub, cidrList, subnet_info) == "OK":
                        for cidr in cidrList:
                            print("test")
                            ec2.create_route(RouteTableId=route_sub['RouteTableId'],
                                            DestinationCidrBlock=cidr,
                                            TransitGatewayId=tgwid)
    #        print(response)
            responseData = {'Success': 'add Route tables.'}
            sendResponse(event, context, responseStatus, responseData)
        else:
    #        print(response)
            responseData = {'Success': 'add Route Pass - Prod is pass.'}
            sendResponse(event, context, responseStatus, responseData)     
    except:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)        
        responseStatus = 'FAILED'
        responseData = {'Failed': 'Failed to add route tables.'}
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

def check_helper(routes_help, route_sub_help, cidrList_help, subnet_info_help):
    for x in routes_help:
        if 'DestinationCidrBlock' in x.keys() and x['DestinationCidrBlock'] in cidrList_help:
            return "PASS"
        else:
            if 'SubnetId' in route_sub_help.keys():
                if route_sub_help['SubnetId'] in subnet_info_help:
                    return "OK"

# if __name__ == '__main__':
#    handler('event', 'handler')