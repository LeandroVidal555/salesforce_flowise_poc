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
                "arn:aws:logs:${REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/lambda/${COMMON_PREFIX}-${ENV}-tools:*"
            ]
        },
        {
            "Description": "S3",
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::${COMMON_PREFIX}-${ENV}-files/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter"
            ],
            "Resource": "arn:aws:ssm:${REGION}:${AWS_ACCOUNT_ID}:*"
        },
        {
            "Description": "Secrets Manager",
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetResourcePolicy",
                "secretsmanager:GetSecretValue",
                "secretsmanager:DescribeSecret",
                "secretsmanager:ListSecretVersionIds"
            ],
            "Resource": [
                "arn:aws:secretsmanager:${REGION}:${AWS_ACCOUNT_ID}:secret:sf-fw-poc-gmail-app-password-*"
            ]
        }
    ]
}