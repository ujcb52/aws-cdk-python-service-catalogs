from aws_cdk import (
  aws_s3 as s3,
  aws_ssm as ssm,
  core
)


class S3Stack(core.Stack):
    def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        upload_bucket_name = core.CfnParameter(self, "uploadBucketName", type="String",
          description="The name of the Amazon S3 bucket where uploaded files will be stored.")
        # bucket = Bucket(self, "myBucket", 
        #   bucket_name=upload_bucket_name.value_as_string)

        # core.CfnParameter
        # ssm.StringParameter
        s3bucket = s3.Bucket(
            self,
            id = "product-s3-sample",
            bucket_name=upload_bucket_name.value_as_string,
            # bucket_name = "prouduct-s3-sample-bucket",
            removal_policy = core.RemovalPolicy.DESTROY,
            versioned = False
        )

