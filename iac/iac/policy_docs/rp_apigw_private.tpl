{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Deny",
            "Principal": "*",
            "Action": "execute-api:Invoke",
            "Resource": "execute-api:/api/POST/v1/tools_backend",
            "Condition": {
                "StringNotEquals": {
                    "aws:sourceVpc": "${VPC_ID}"
                }
            }
        },
        {
            "Effect": "Allow",
            "Principal": "*",
            "Action": "execute-api:Invoke",
            "Resource": "execute-api:/api/POST/v1/tools_backend"
        }
    ]
}