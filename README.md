# gp3 migration utility v1.0

This repository contains code that makes it easy for AWS customers to upgrade to the latest EBS gp3 volumes. By migrating to gp3, customers can save up to 20% lower price-point per GB than existing gp2 volumes.

## Table of Contents
1. [Pre-requisites](#Pre)
1. [Getting Started](#Start)
1. [Key Details (Do not skip this section)](#Key)
1. [Next Steps](#Next)
1. [License](#License)

## Pre-requisites <a name="Pre"></a>

This release of the gp3 migration utility requires some manual setup. The next release will include SAM and CloudFormation templates that will make it easy to deploy and run this utility in your target AWS account.

1. You will need the AWS CLI and/or access to the AWS Console
2. Create a DynamoDB table with on-demand capacity mode in your target AWS account and region with a partition key named `volume_id`
3. Create an standard SNS topic using  default options in the same account and region as your DynamoDB table. Create an email subscription against this topic and note down the resource ARN.

## Getting Started <a name="Start"></a>

1. Create an IAM role for Lambda to use
```bash
aws iam create-role --role-name <name of your IAM role> --assume-role-policy-document file://lambda_trust_policy.json
```

1. Create an IAM policy that will be used by the IAM role you created in the previous step. Note down the ARN for the newly created policy.
```bash
aws iam create-policy --policy-name <name of your IAM policy> --policy-document file://gp3_migrate_policy.json
```

1. Attach the IAM policy to the role.
```bash
aws iam attach-role-policy --policy-arn arn:aws:iam::1234567890:policy/<name of your IAM policy> --role-name <name of your IAM role>
```

1. Create a Lambda function from scratch

- Choose Python 3.8 for the run time
- Use the IAM role you created in the previous steps
- You can choose "None" for VPC or select any VPC in your account that can access the AWS APIs.
- If you are using the AWS console, delete the skeleton Lambda code and paste in the contents of the file `gp3_migrate.py`
- Add in the appropriate values for your DynamoDB table name and SNS topic.
- Leave Lamda memory at 128 MB
- Change the timeout to 1 minute

## Key Details (Do not skip this section) <a name="Key"></a>

> IMPORTANT: Please note that upon execution, this program by default will upgrade ALL gp2 EBS volumes in your account to gp3. If you need to back out, there is no easy button in this version of the program. If you need to go back from gp3 to gp2 this will have to be done manually. You can [modify](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/requesting-ebs-volume-modifications.html) your volume(s) using the Console/CLI/SDK. In some cases, the modify volume operation may fail and you may need to wait for 6 hours before you can modify your volume(s) back to gp2. For more details please see the limitations [here](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/modify-volume-requirements.html#elastic-volumes-limitations).

There will be no changes made to any of your other EBS volume types like io1, io2, sc1, st1, etc. If you have any gp2 EBS volumes that you don't want upgraded, you will need to tag each EBS volume with the key **upgrade_to_gp3** and set the value to ***no*** or ***false***. This will make the program skip those volumes and they will be untouched.

You will need to run your Lambda program at least two times and wait at least 60 seconds before each run. There is no limit to the number of times you can run your Lambda. The first execution will kick off the upgrade from gp2 to gp3. Depending on the number and size of EBS volumes in you account, you will need to wait for a few minutes for the conversion to complete. The subsequent runs after the first run will do a status check and send an email (via SNS) with a summary of the results.

## Next Steps <a name="Next"></a>

We are actively iterating on this program to add more features and functionality.  We'd love to get your input and hear from you. Please create any Github issues for additional features you'd like to see. 

## License <a name="License"></a>

This library is licensed under the MIT-0 License. See the LICENSE file.
