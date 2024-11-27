{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Description": "CloudWatch - logs creation",
            "Effect": "Allow",
            "Action": "logs:CreateLogGroup",
            "Resource": "arn:aws:logs:${REGION}:${AWS_ACCOUNT_ID}:*"
        },
        {
            "Description": "CloudWatch - logs write",
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:${REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/lambda/${COMMON_PREFIX}-${ENV}-graph:*"
            ]
        }
    ]
}