import aws_cdk as cdk

from aws_cdk import(
    aws_s3 as s3
)


class S3Stack(cdk.Stack):

    def __init__(self, scope: cdk.App, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cg = config["global"]
        cs = config["s3"]

        #####################################################
        ##### TAGS ##########################################
        #####################################################

        cdk.Tags.of(self).add("Owner", cg["tags"]["owner"])
        cdk.Tags.of(self).add("Project", cg["tags"]["project"])
        cdk.Tags.of(self).add("Environment", cg["tags"]["env"])
        cdk.Tags.of(self).add("PrimaryContact", cg["tags"]["contact"])


        #####################################################
        ##### S3 Files Bucket ###############################
        #####################################################

        s3.Bucket(self, "FilesBucket",
            bucket_name = f"{cg['common_prefix']}-{cg['env']}-files",
            removal_policy = cdk.RemovalPolicy.DESTROY,
            auto_delete_objects = True, # delete object when deleting the bucket from the stack
        )