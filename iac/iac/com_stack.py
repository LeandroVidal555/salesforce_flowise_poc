import aws_cdk as cdk

from aws_cdk import(
    aws_ec2 as ec2,
    aws_events as events,
    aws_events_targets as events_targets,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_lambda_python_alpha as _lambda_py,
    aws_s3 as s3,
    aws_ssm as ssm
)

import boto3


def iac_output(value):
    """logging solution: write the output to an ssm parameter"""
    value = str(value)
    
    # ssm param value máx length is 4096 chars, truncate if exceeded
    if len(value) > 4096:
        value = value[:4085] + "[truncated]"

    ssm_client = boto3.client('ssm')
    ssm_client.put_parameter(Name="iac-output", Value=value, Type='String', Overwrite=True)


class ComputeStack(cdk.Stack):

    def __init__(self, scope: cdk.App, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cg = config["global"]
        cs = config["compute"]

        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_name=f"{cg['common_prefix']}-{cg['env']}-vpc")
        role_ec2 = iam.Role.from_role_name(self, "Role_EC2", role_name=f"{cg['common_prefix']}-{cg['env']}-ec2-role")
        role_lambda = iam.Role.from_role_name(self, "Role_lambda", role_name=f"{cg['common_prefix']}-{cg['env']}-lambda-role")
        sg_ec2 = ec2.SecurityGroup.from_lookup_by_name(self, "SG_EC2", security_group_name=f"{cg['common_prefix']}-{cg['env']}-ec2-sg", vpc=vpc)
        #sg_lambda = ec2.SecurityGroup.from_lookup_by_name(self, "SG_LAMBDA", security_group_name=f"{cg['common_prefix']}-{cg['env']}-lambda-sg", vpc=vpc)


        #####################################################
        ##### TAGS ##########################################
        #####################################################

        cdk.Tags.of(self).add("Owner", cg["tags"]["owner"])
        cdk.Tags.of(self).add("Project", cg["tags"]["project"])
        cdk.Tags.of(self).add("Environment", cg["tags"]["env"])
        cdk.Tags.of(self).add("PrimaryContact", cg["tags"]["contact"])


        #####################################################
        ##### EC2 ###########################################
        #####################################################

        volume = ec2.BlockDevice(
            device_name=cs["ebs_device_name"],
            volume=ec2.BlockDeviceVolume.ebs(
                volume_size=27,
                volume_type=ec2.EbsDeviceVolumeType.GP3,
                delete_on_termination=False
            )
        )
        
        keypair_ec2 = ec2.KeyPair.from_key_pair_name(self, "KeyPair_EC2_Import", f"{cg['common_prefix']}-{cg['env']}-keypair")

        # Define the EC2 instance
        ec2_instance = ec2.Instance(
            self, "EC2_Instance",
            instance_name=f"{cg['common_prefix']}-{cg['env']}-flowise",
            instance_type=ec2.InstanceType(cs["ec2_machine_type"]),
            #machine_image=ec2.MachineImage.latest_amazon_linux2023(),
            machine_image=ec2.MachineImage.generic_linux({
                cg['region']: cs['ec2_machine_ami']
            }),
            block_devices=[volume],
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            security_group=sg_ec2,
            key_pair=keypair_ec2,
            role=role_ec2,
            user_data_causes_replacement=True
        )

        # Read user data script and load it to the EC2 Backend instance's config
        with open("iac/ec2_user_data/ec2_user_data.sh", 'r') as file:
            user_data = file.read()

        ec2_instance.add_user_data(user_data)

        ssm.StringParameter(
            self, "SSMParam_EC2_DNS",
            parameter_name=f"/{cg['common_prefix']}-{cg['env']}/pipeline/ec2_instance_dns",
            string_value=ec2_instance.instance_public_dns_name
        )


        #####################################################
        ##### Lambda Processor Function #####################
        #####################################################

        # alpha lambda fn class: installs deps automatically
        lambda_fn_proc = _lambda_py.PythonFunction(
            self, "Lambda_Process_Function",
            function_name=f"{cg['common_prefix']}-{cg['env']}-process",
            entry="iac/lambda_code/process",
            environment=cs['lambda_envvars_process'],
            index="lambda_function.py", 
            handler="lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            role=role_lambda,
            memory_size=512,
            timeout=cdk.Duration.seconds(120),
            #vpc=vpc,
            #security_groups=[sg_lambda]
        )

        s3_bucket = s3.Bucket.from_bucket_name(self, "FilesBucket", f"{cg['common_prefix']}-{cg['env']}-files")

        # this layer contains leptonic+tesseract binaries
        layer_asset = _lambda.LayerVersion(
            self, "TesseractLayer",
            code=_lambda.Code.from_bucket(
                bucket=s3_bucket,
                key="layers/tesseract-layer.zip"
            ),
            compatible_runtimes=[
                _lambda.Runtime.PYTHON_3_12
            ],
            description="Lambda layer with Leptonica and Tesseract binaries",
            layer_version_name=f"{cg['common_prefix']}-{cg['env']}-tesseract-layer",
        )

        lambda_fn_proc.add_layers(layer_asset)


        #####################################################
        ##### Lambda Graph Function #########################
        #####################################################

        # alpha lambda fn class: installs deps automatically
        _lambda_py.PythonFunction(
            self, "Lambda_Graph_Function",
            function_name=f"{cg['common_prefix']}-{cg['env']}-graph",
            entry="iac/lambda_code/graph",
            environment=cs['lambda_envvars_graph'],
            index="lambda_function.py", 
            handler="lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            role=role_lambda,
            timeout=cdk.Duration.seconds(15)
        )


        #####################################################
        ##### EventBridge ###################################
        #####################################################

        # Reference the existing SalesForce EventBus by its ARN or name
        existing_event_bus = events.EventBus.from_event_bus_arn(
            self, "SF_EventBus",
            event_bus_arn=cs['event_bus_arn']
        )

        # Create SalesForce EventBridge rule in the existing SalesForce EventBus for ImportFile event
        rule_file = events.Rule(
            self, "SF_EventRule_File",
            rule_name=f"{cg['common_prefix']}-{cg['env']}-importfile-rule",
            event_bus=existing_event_bus,  # Link the existing EventBus
            event_pattern={
                "source": [cs['event_bus_arn'].split("event-bus/")[1]],
                "detail_type": ["Import_Event__e"],
                "detail": { "payload": { "Action__c": ["ImportFile"] } }
            },
            description="Rule to trigger Lambda on SF event",
            enabled=True
        )

        # Add the Lambda Processor Function as a target of the rule
        rule_file.add_target(events_targets.LambdaFunction(lambda_fn_proc))

        # Create SalesForce EventBridge rule in the existing SalesForce EventBus for ImportText event
        rule_text = events.Rule(
            self, "SF_EventRule_Text",
            rule_name=f"{cg['common_prefix']}-{cg['env']}-importtext-rule",
            event_bus=existing_event_bus,  # Link the existing EventBus
            event_pattern={
                "source": [cs['event_bus_arn'].split("event-bus/")[1]],
                "detail_type": ["Import_Event__e"],
                "detail": { "payload": { "Action__c": ["ImportText"] } }
            },
            description="Rule to trigger Lambda on SF event",
            enabled=True
        )

        # Add the Lambda Processor Function as a target of the rule
        rule_text.add_target(events_targets.LambdaFunction(lambda_fn_proc))