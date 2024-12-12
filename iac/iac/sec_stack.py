import aws_cdk as cdk

from aws_cdk import(
    aws_ec2 as ec2,
    aws_iam as iam,
)

import json

def attach_policy_doc(scope, file, role):
    """Add a policy to a role, providing a json file name"""

    with open(f"iac/policy_docs/{file}.json", 'r') as policy_file:
        data = policy_file.read()
        policy_dict = json.loads(data)

    # To CamelCase
    id_prefix = "".join([part.capitalize() for part in file.split('_')])

    role.attach_inline_policy(iam.Policy(scope, f"{id_prefix}Permissions",
        document = iam.PolicyDocument.from_json(policy_dict),
    ))


class SecurityStack(cdk.Stack):

    def __init__(self, scope: cdk.App, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cg = config["global"]
        cs = config["security"]

        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_name=f"{cg['common_prefix']}-{cg['env']}-vpc")

        #####################################################
        ##### TAGS ##########################################
        #####################################################

        cdk.Tags.of(self).add("Owner", cg["tags"]["owner"])
        cdk.Tags.of(self).add("Project", cg["tags"]["project"])
        cdk.Tags.of(self).add("Environment", cg["tags"]["env"])
        cdk.Tags.of(self).add("PrimaryContact", cg["tags"]["contact"])
        

        #####################################################
        ##### RDS POSTGRES ##################################
        #####################################################

        # Create a security group for the RDS instance
        sg_postgres = ec2.SecurityGroup(
            self, "SG_PGres",
            security_group_name = f"{cg['common_prefix']}-{cg['env']}-pgres-sg",
            vpc = vpc,
            description = "Allow access from EC2 instance"
        )


        #####################################################
        ##### EC2 ###########################################
        #####################################################

        # Create an IAM Role for the EC2 instance
        role_ec2 = iam.Role(
            self, "Role_EC2",
            role_name = f"{cg['common_prefix']}-{cg['env']}-ec2-role",
            assumed_by = iam.ServicePrincipal("ec2.amazonaws.com"),
            managed_policies = [
                iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore")
            ],
            description="Role for the EC2 instance"
        )
        attach_policy_doc(self, "role_ec2", role_ec2)

        # Create a security group for the ALB pointing to EC2 instance
        #sg_alb_ec2 = ec2.SecurityGroup(
        #    self, "SG_ALB_WS",
        #    security_group_name = f"{cg['common_prefix']}-{cg['env']}-alb-ws-sg",
        #    vpc = vpc,
        #    description = "SG for ALB pointing to the WebServer in EC2 instance"
        #)

        # Add rules to allow access from 8080 CloudFront origins
        #sg_alb_ec2.add_ingress_rule(
        #    peer=ec2.Peer.prefix_list(cs['cf_prefix_list']),
        #    connection=ec2.Port.tcp(8080),
        #    description="Allow HTTPS traffic only from 8080 CloudFront origins"
        #)

        # Create a security group for the EC2 instance
        sg_ec2 = ec2.SecurityGroup(
            self, "SG_EC2",
            security_group_name = f"{cg['common_prefix']}-{cg['env']}-ec2-sg",
            vpc = vpc,
            description = "SG for EC2 instance"
        )

        # Allow traffic from CF
        sg_ec2.add_ingress_rule(
            peer=ec2.Peer.ipv4(cs['local_ip']),
            connection=ec2.Port.tcp(22),
            description="Allow SSH traffic from local PC"
        )

        # Allow traffic from CF - API
        sg_ec2.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(80),
            description="Allow traffic from CF - API"
        )

        # Allow traffic from CF - UI
        sg_ec2.add_ingress_rule(
            peer=ec2.Peer.prefix_list(cs['cf_prefix_list']),
            connection=ec2.Port.tcp(3000),
            description="Allow traffic from CF - UI"
        )
        

        # Add rules to allow access to RDS from the EC2 instance
        sg_postgres.add_ingress_rule(peer=sg_ec2, connection=ec2.Port.tcp(cs["pgres_port"]))
        # sg_postgres.add_ingress_rule(peer=nlb_ip1, connection=ec2.Port.tcp(cs["pgres_port"]))
        # sg_postgres.add_ingress_rule(peer=nlb_ip2, connection=ec2.Port.tcp(cs["pgres_port"]))


        #####################################################
        ##### Lambda ########################################
        #####################################################

        # Create an IAM Role for the Lambda Processor function
        role_lambda_process = iam.Role(
            self, "Role_Lambda_Process",
            role_name = f"{cg['common_prefix']}-{cg['env']}-lambda-process-role",
            assumed_by = iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for the Lambda Processor function"
        )
        attach_policy_doc(self, "role_lambda_process", role_lambda_process)

        # Create an IAM Role for the Lambda Graphs function
        role_lambda_graph = iam.Role(
            self, "Role_Lambda_Graph",
            role_name = f"{cg['common_prefix']}-{cg['env']}-lambda-graph-role",
            assumed_by = iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for the Lambda Graph function"
        )
        attach_policy_doc(self, "role_lambda_graph", role_lambda_graph)

        # Create an IAM Role for the Tools Lambda function
        role_lambda_tools = iam.Role(
            self, "Role_Lambda_Tools",
            role_name = f"{cg['common_prefix']}-{cg['env']}-lambda-tools-role",
            assumed_by = iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for the Tools Lambda function"
        )
        attach_policy_doc(self, "role_lambda_tools", role_lambda_tools)

        # Create a security group for the VPC Endpoint
        sg_vpc_ep = ec2.SecurityGroup(
            self, "SG_VPC_EP",
            security_group_name = f"{cg['common_prefix']}-{cg['env']}-vpc-ep-sg",
            vpc = vpc,
            description = "SG for VPC Endpoint"
        )

        # Allow traffic from EC2
        sg_vpc_ep.add_ingress_rule(
            peer=ec2.Peer.security_group_id(sg_ec2.security_group_id),
            connection=ec2.Port.tcp(443),
            description="Allow HTTPS traffic from EC2"
        )
