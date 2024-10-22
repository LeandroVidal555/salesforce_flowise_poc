import aws_cdk as cdk

from aws_cdk import(
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as cf_origins,
    aws_ec2 as ec2,
    aws_ssm as ssm
)


class AccessStack(cdk.Stack):

    def __init__(self, scope: cdk.App, construct_id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cg = config["global"]
        cs = config["access"]

        vpc = ec2.Vpc.from_lookup(self, "VPC", vpc_name=f"{cg['common_prefix']}-{cg['env']}-vpc")

        #sg_alb_ws = ec2.SecurityGroup.from_lookup_by_name(self, "SG_ALB_WS", security_group_name=f"{cg['common_prefix']}-{cg['env']}-alb-ws-sg", vpc=vpc)

        ec2_instance_dns = ssm.StringParameter.from_string_parameter_name(
            self, "SSMParam_EC2_DNS",
            string_parameter_name=f"/{cg['common_prefix']}-{cg['env']}/pipeline/ec2_instance_dns"
        ).string_value

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
        cloudfront.Distribution(
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