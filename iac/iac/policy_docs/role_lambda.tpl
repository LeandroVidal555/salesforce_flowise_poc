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
                "arn:aws:logs:${REGION}:${AWS_ACCOUNT_ID}:log-group:/aws/lambda/${COMMON_PREFIX}-${ENV}-process:*"
            ]
        },
        {
            "Description": "DynamoDB",
            "Effect": "Allow",
            "Action": [
                "dynamodb:BatchWriteItem",
                "dynamodb:PutItem"
            ],
            "Resource": "arn:aws:dynamodb:${REGION}:${AWS_ACCOUNT_ID}:table/${COMMON_PREFIX}-${ENV}-extxt-table"
        },
        {
            "Description": "S3",
            "Effect": "Allow",
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::${COMMON_PREFIX}-${ENV}-files/*"
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
                "arn:aws:secretsmanager:${REGION}:${AWS_ACCOUNT_ID}:secret:${COMMON_PREFIX}-${ENV}-connected-app-creds-*",
                "arn:aws:secretsmanager:${REGION}:${AWS_ACCOUNT_ID}:secret:${COMMON_PREFIX}-${ENV}-fw-api-key-*"
            ]
        },
        {
            "Description": "Secrets Manager",
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": [
                "arn:aws:secretsmanager:${REGION}:${AWS_ACCOUNT_ID}:secret:${COMMON_PREFIX}-${ENV}-pgres-creds-*"
            ]
        },
        {
            "Description": "PGres DB connection",
            "Effect": "Allow",
            "Action": [
                "rds-db:connect"
            ],
            "Resource": [
                "arn:aws:rds-db:${REGION}:${AWS_ACCOUNT_ID}:dbuser:${PGRES_ID}/epwery"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterface",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DeleteNetworkInterface",
                "ec2:AttachNetworkInterface"
            ],
            "Resource": "*"
        }
    ]
}