#!/bin/bash

SHELL_DIR=$(dirname $0)
# REGION=$(aws configure get region)
REGION="ap-northeast-2"

MAJOR_VER=0
MINOR_VER=1
VER=$(date +%Y%m%d-%H%M%S)
sed -i -e "s|PF_VERSION = .*|PF_VERSION = \"v${MAJOR_VER}.${MINOR_VER}.${VER}\"|" "${SHELL_DIR}/service_catalog_cdk/catalog_stack.py"
#sed -i -e "s|PF_VERSION = .*|PF_VERSION = \"v${MAJOR_VER}.${MINOR_VER}.${VER}\"|" "${SHELL_DIR}/service_catalog_cdk/instance_catalog_stack.py"

CFN_PRODUCT_PATH="${SHELL_DIR}/products/cfn"
CFN_STACKSET_PATH="${SHELL_DIR}/stacksets/cfn"

BUCKET="11st-master-seoul-service-catalog-cdk-created"
BUCKET_PRODUCT_PATH="s3://${BUCKET}/products/cfn"
BUCKET_STACKSET_PATH="s3://${BUCKET}/stacksets/cfn"

PRODUCT_LIST=$(cdk ls | grep product)
STACKSET_LIST=$(cdk ls | grep stackset)

mkdir -p ${CFN_PRODUCT_PATH}
mkdir -p ${CFN_STACKSET_PATH}

for product in ${PRODUCT_LIST}; do
  ## create product cloud formation yaml
  echo "cdk synth ${product} > ${CFN_PRODUCT_PATH}/${product}.yaml"
  cdk synth ${product} > ${CFN_PRODUCT_PATH}/${product}.yaml

#  BUCKET_URL="https://${BUCKET}.s3.${REGION}.amazonaws.com/products/cfn/${product}.yaml"
#  JSON_STRING=$( jq -n \
#                --arg nm "${product}" \
#                --arg val "${BUCKET_URL}" \
#                '{
#                  "Name": $nm,
#                  "Value": $val,
#                  "Type": "String"
#                }'
#                )
#  aws ssm put-parameter --cli-input-json "${JSON_STRING}" --overwrite
done


for stackset in ${STACKSET_LIST}; do
  ## create stackset cloud formation yaml
  echo "cdk synth ${stackset} > ${CFN_STACKSET_PATH}/${stackset}.yaml"
  cdk synth ${stackset} > ${CFN_STACKSET_PATH}/${stackset}.yaml

#  BUCKET_URL="https://${BUCKET}.s3.${REGION}.amazonaws.com/stacksets/cfn/${stackset}.yaml"
#  JSON_STRING=$( jq -n \
#                --arg nm "${stackset}" \
#                --arg val "${BUCKET_URL}" \
#                '{
#                  "Name": $nm,
#                  "Value": $val,
#                  "Type": "String"
#                }'
#                )
#  aws ssm put-parameter --cli-input-json "${JSON_STRING}" --overwrite
done

## upload to s3
aws s3 sync "${CFN_PRODUCT_PATH}" "${BUCKET_PRODUCT_PATH}"
aws s3 sync "${CFN_STACKSET_PATH}" "${BUCKET_STACKSET_PATH}"

