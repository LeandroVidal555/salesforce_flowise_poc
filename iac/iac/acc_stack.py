import aws_cdk as cdk
import json

from aws_cdk import(
    aws_apigateway as apigw,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cf_origins,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_lambda as _lambda,
    aws_ssm as ssm
)

def get_policy_doc(file, vpc_id):
    """Returns a PolicyDocument object, providing a json file name"""

    with open(f"iac/policy_docs/{file}.json", 'r') as policy_file:
        data = policy_file.read()
        data = data.replace("${VPC_ID}", vpc_id)

        policy_dict = json.loads(data)

        return iam.PolicyDocument.from_json(policy_dict)


class AccessStack(cdk.Stack):

    def __init__(self, scope: cdk.App, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cg = config["global"]
        cs = config["access"]

        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_name=f"{cg['common_prefix']}-{cg['env']}-vpc")

        #sg_alb_ws = ec2.SecurityGroup.from_lookup_by_name(self, "SG_ALB_WS", security_group_name=f"{cg['common_prefix']}-{cg['env']}-alb-ws-sg", vpc=vpc)
        sg_vpc_ep = ec2.SecurityGroup.from_lookup_by_name(self, "SG_VPC_EP", security_group_name=f"{cg['common_prefix']}-{cg['env']}-vpc-ep-sg", vpc=vpc)

        ec2_instance_dns = ssm.StringParameter.from_string_parameter_name(
            self, "SSMParam_EC2_DNS",
            string_parameter_name=f"/{cg['common_prefix']}-{cg['env']}/pipeline/ec2_instance_dns"
        ).string_value

        lambda_fn_process = _lambda.Function.from_function_name(
            self, "Lambda_Process_Function",
            function_name=f"{cg['common_prefix']}-{cg['env']}-process"
        )

        lambda_fn_graph = _lambda.Function.from_function_name(
            self, "Lambda_Graph_Function",
            function_name=f"{cg['common_prefix']}-{cg['env']}-graph"
        )

        lambda_fn_tools = _lambda.Function.from_function_name(
            self, "Lambda_Tools_Function",
            function_name=f"{cg['common_prefix']}-{cg['env']}-tools"
        )


        #####################################################
        ##### TAGS ##########################################
        #####################################################

        cdk.Tags.of(self).add("Owner", cg["tags"]["owner"])
        cdk.Tags.of(self).add("Project", cg["tags"]["project"])
        cdk.Tags.of(self).add("Environment", cg["tags"]["env"])
        cdk.Tags.of(self).add("PrimaryContact", cg["tags"]["contact"])


        #####################################################
        ##### LOAD BALANCING - EC2 ALB ######################
        #####################################################

        """
        secret_cf_key = secretsmanager.Secret(
            self, "Secret_CF_Header_Key",
            secret_name=f"{cg['common_prefix']}-{cg['env']}-cf-header-key",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                exclude_punctuation=True,
                exclude_uppercase=True
            )
        ).secret_value.unsafe_unwrap()

        # Create the ALB
        alb_ws = elbv2.ApplicationLoadBalancer(
            self, "ALB_WebServer",
            load_balancer_name=f"{cg['common_prefix']}-{cg['env']}-webserver-alb",
            vpc=vpc,
            internet_facing=True,
            security_group=sg_alb_ws
        )
        
        tg_alb_ws = elbv2_targets.InstanceIdTarget(
            instance_id=ec2_instance_id,
            port=8080
        )

        # Add a listener for HTTP
        listener = alb_ws.add_listener(
            "Listener_ALB_WebServer",
            port=8080,
            open=True,
            default_action=elbv2.ListenerAction.fixed_response(
                status_code=400,
                content_type="text/plain",
                message_body="Bad request or wrong header key"
            )
        )

        # Add the default action to forward to the target group
        listener.add_targets(
            "TG_ALB_WebServer",
            target_group_name=f"{cg['common_prefix']}-{cg['env']}-alb-ws-tg",
            port=8080,
            targets=[tg_alb_ws],
            conditions=[
                elbv2.ListenerCondition.http_header(
                    name="x-cloudfront-secret-key",
                    values=[secret_cf_key]
                ),
                elbv2.ListenerCondition.path_patterns(
                    values=["/api/*"]
                )
            ],
            priority=1,
            health_check=elbv2.HealthCheck(
                path="/",
                port="8080",
                protocol=elbv2.Protocol.HTTP,
                healthy_threshold_count=2,
                interval=cdk.Duration.seconds(15)
            )
        )
        """

        
        #####################################################
        ##### CLOUDFRONT - EC2 Webservice ###################
        #####################################################
    
        # CloudFront origin pointing to the ALB in front of the EC2 instance
        #origin = cf_origins.HttpOrigin(
        #    domain_name=alb_ws.load_balancer_dns_name,
        #    http_port=8080,
        #    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        #    custom_headers={"x-cloudfront-secret-key": secret_cf_key}
        #)

        be_origin_80 = cf_origins.HttpOrigin(
            domain_name=ec2_instance_dns, # EC2 instance public DNS
            http_port=80,
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        )

        #be_origin_443 = cf_origins.HttpOrigin(
        #    domain_name=, # EC2 instance public DNS
        #    http_port=443,
        #    protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
        #)

        ui_origin = cf_origins.HttpOrigin(
            domain_name=ec2_instance_dns, # EC2 instance public DNS
            http_port=3000,
            protocol_policy=cloudfront.OriginProtocolPolicy.HTTP_ONLY,
            read_timeout=cdk.Duration.seconds(60)
        )
        
        cache_policy_be = cloudfront.CachePolicy.CACHING_DISABLED if cs["cache_policy_be"] == "disabled" else cloudfront.CachePolicy.CACHING_OPTIMIZED
        cache_policy_ui = cloudfront.CachePolicy.CACHING_DISABLED if cs["cache_policy_ui"] == "disabled" else cloudfront.CachePolicy.CACHING_OPTIMIZED
        # CloudFront distribution
        cf_distro = cloudfront.Distribution(
            self, "CF_WS_Distribution",
            default_behavior=cloudfront.BehaviorOptions(
                origin=ui_origin,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                cache_policy=cache_policy_ui,
                origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER_EXCEPT_HOST_HEADER,
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS
            ),
            additional_behaviors={
                "/api_80/*": cloudfront.BehaviorOptions(
                    origin=be_origin_80,
                    allowed_methods=cloudfront.AllowedMethods.ALLOW_ALL,
                    cache_policy=cache_policy_be,
                    origin_request_policy=cloudfront.OriginRequestPolicy.ALL_VIEWER,
                    response_headers_policy=cloudfront.ResponseHeadersPolicy.CORS_ALLOW_ALL_ORIGINS_WITH_PREFLIGHT_AND_SECURITY_HEADERS,
                    viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.HTTPS_ONLY
                )
            },
            price_class = cloudfront.PriceClass.PRICE_CLASS_100
        )

        ssm.StringParameter(
            self, "SSMParam_CF_DISTRO_DOMAIN",
            parameter_name=f"/{cg['common_prefix']}-{cg['env']}/pipeline/cf_distro_domain",
            string_value=cf_distro.distribution_domain_name
        )

        
        #####################################################
        ##### API GATEWAY ###################################
        #####################################################

        ### Base API for all public lambdas
        ###################################
        api_lambda = apigw.RestApi(
            self, "APIGW_API_LAMBDA",
            rest_api_name = f"/{cg['common_prefix']}-{cg['env']}-lambda-api",
            cloud_watch_role = True,
            deploy_options = apigw.StageOptions(
                stage_name = "api",
                logging_level = apigw.MethodLoggingLevel.INFO,
                data_trace_enabled = True,
                metrics_enabled = True,
                tracing_enabled = True
            )
        )

        api_key = api_lambda.add_api_key(
            "APIGW_API_LAMBDA_KEY",
            api_key_name=f"/{cg['common_prefix']}-{cg['env']}-lambda-api-key"
        )

        usage_plan = api_lambda.add_usage_plan(
            "APIGW_LAMBDA_UsagePlan",
            name=f"/{cg['common_prefix']}-{cg['env']}-lambda-usage-plan"
        )

        usage_plan.add_api_key(api_key)

        usage_plan.add_api_stage(
            stage=api_lambda.deployment_stage
        )

        api_version = api_lambda.root.add_resource("v1")


        # Processor Lambda API (Non-SF API)
        api_ep = api_version.add_resource(
            "event_import",
            default_method_options=apigw.MethodOptions(api_key_required=True)
        )

        integration = apigw.LambdaIntegration(lambda_fn_process, proxy=True)
        api_ep.add_method(
            "POST",
            integration,
            request_parameters={"method.request.path.proxy": True}
        )

        lambda_fn_process.add_permission(
            "API_GW_InvokeProcessorLambda",
            principal = iam.ServicePrincipal("apigateway.amazonaws.com"),
            action = "lambda:InvokeFunction",
            source_arn = f"arn:aws:apigateway:{cg['region']}::/restapis/{api_lambda.rest_api_id}"
        )


        # Graph Lambda API
        api_ep = api_version.add_resource(
            "graph",
            default_method_options=apigw.MethodOptions(api_key_required=True)
        )

        integration = apigw.LambdaIntegration(lambda_fn_graph, proxy=True)
        api_ep.add_method(
            "POST",
            integration,
            request_parameters={"method.request.path.proxy": True}
        )

        lambda_fn_graph.add_permission(
            "API_GW_InvokeGraphLambda",
            principal = iam.ServicePrincipal("apigateway.amazonaws.com"),
            action = "lambda:InvokeFunction",
            source_arn = f"arn:aws:apigateway:{cg['region']}::/restapis/{api_lambda.rest_api_id}"
        )

        ### Base API for all private lambdas
        ####################################
        vpc_ep = ec2.InterfaceVpcEndpoint(
            self, "APIGW_VPC_EP",
            private_dns_enabled=True,
            vpc=vpc,
            service=ec2.InterfaceVpcEndpointService(
                name=f"com.amazonaws.{cg['region']}.execute-api"
            ),
            subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[sg_vpc_ep]
        )

        api_lambda_priv = apigw.RestApi(
            self, "APIGW_API_PRIV_LAMBDA",
            rest_api_name = f"/{cg['common_prefix']}-{cg['env']}-priv-lambda-api",
            cloud_watch_role = True,
            deploy_options = apigw.StageOptions(
                stage_name = "api",
                logging_level = apigw.MethodLoggingLevel.INFO,
                data_trace_enabled = True,
                metrics_enabled = True,
                tracing_enabled = True
            ),
            endpoint_configuration = apigw.EndpointConfiguration(
                types=[apigw.EndpointType.PRIVATE],
                vpc_endpoints=[vpc_ep]
            ),
            policy = get_policy_doc("rp_apigw_private", vpc.vpc_id)
        )

        # Tools Lambda function API
        api_version_priv = api_lambda_priv.root.add_resource("v1")
        api_ep_priv = api_version_priv.add_resource("tools_backend")

        integration = apigw.LambdaIntegration(lambda_fn_tools, proxy=True)

        api_ep_priv.add_method(
            "POST",
            integration,
            request_parameters={"method.request.path.proxy": True}
        )

        lambda_fn_tools.add_permission(
            "API_GW_InvokeToolsLambda",
            principal = iam.ServicePrincipal("apigateway.amazonaws.com"),
            action = "lambda:InvokeFunction",
            #source_arn = f"arn:aws:apigateway:{cg['region']}::/restapis/{api_lambda_priv.rest_api_id}"
            source_arn = f"arn:aws:execute-api:{cg['region']}:{cg['account']}:{api_lambda_priv.rest_api_id}/*/POST/v1/tools_backend"
        )