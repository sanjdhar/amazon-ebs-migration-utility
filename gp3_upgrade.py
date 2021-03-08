import boto3
import json
import decimal
from botocore.exceptions import ClientError
from datetime import datetime

def lambda_handler(event, context):
    
    # Create a DynamoDB table with a simple primary key "volume_id" and input the name in the below variable
    DDB_TABLE_NAME = "gp3_upgrade"

    SNS_ARN="arn:aws:sns:us-east-1:065399810791:gp3_upgrade"

    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table(DDB_TABLE_NAME)

    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']

    ec2_client = boto3.client('ec2')
    ec2 = boto3.resource('ec2')

    sns_client = boto3.client('sns')


    # Helper class to convert a DynamoDB item to JSON.
    class DecimalEncoder(json.JSONEncoder):
        def default(self, o):
            if isinstance(o, decimal.Decimal):
                if abs(o) % 1 > 0:
                    return float(o)
                else:
                    return int(o)
            return super(DecimalEncoder, self).default(o)

    def check_tags(vol_tags, vol_id):
        upgrade_tag = True
        if not vol_tags is None:
            for tag in vol_tags:

                tag_key=tag['Key'].lower()
                tag_val=tag.get('Value').lower()

                if tag_key == 'upgrade_to_gp3' and (tag_val == 'no' or tag_val == 'false'):
                    print("No gp3 upgrade set on: ", vol_id)
                    upgrade_tag = False
            return(upgrade_tag)

        else:
            return(upgrade_tag)



    volume_iterator = ec2.volumes.filter(
        Filters=[
            {
                'Name': 'volume-type',
                'Values': [
                    'gp2',
                ]
            },
        ],

    )

    #Array to hold volume list
    vol_list=[]

    for v in volume_iterator:
        if(check_tags(v.tags, v.id)):
            vol_list.append(v.id)

    response = table.get_item(Key={'volume_id': 'vol-meta-' + account_id})

    if('Item') in response:
        run_cnt = response['Item']['run_seq']
        response = table.update_item(
            Key={
                'volume_id': 'vol-meta-' + account_id,

            },
            UpdateExpression="set run_seq = run_seq + :val",
            ExpressionAttributeValues={
                ':val': decimal.Decimal(1)
            },
            ReturnValues="UPDATED_NEW"
        )



        response = table.get_item(
            Key={
                'volume_id': 'vol-meta-' + account_id,
            }

        )
        vol_list=response['Item']['vol_list']

        for vol in vol_list:
            try:
                volume = ec2.Volume(vol)
                if volume.volume_type == 'gp2':
                    try:
                        vol_mod = ec2_client.modify_volume(
                                    VolumeId = vol,
                                    VolumeType = 'gp3'
                        )
                    except ClientError as e:
                        print(vol + ': ' + e.response['Error']['Message'])
                elif volume.volume_type == 'gp3':
                    response = table.update_item(
                        Key={
                            'volume_id': vol,

                        },
                        ExpressionAttributeNames={"#aft": "after_type"},
                        UpdateExpression="set #aft = :aft",
                        ExpressionAttributeValues={
                        ':aft': "gp3"
                        },
                        ReturnValues="UPDATED_NEW"
                    )

                if (run_cnt > 1):
                    message = 'gp3 volume upgrade status as of ' + datetime.utcnow().strftime("%b %d %Y %H:%M:%S UTC") + ':\n'
                    message = message + """\n-------------\t\t\t\t-------------\t\t\t\t--------------\n
    Volume ID\t\t\t\tAccount ID\t\t\t\tStatus\n-------------\t\t\t\t-------------\t\t\t\t--------------\n
    """
                    response = table.get_item(
                    Key={
                        'volume_id': 'vol-meta-' + account_id,
                        }

                    )
            except ClientError as e:
                print(e.response['Error']['Message'])

        vol_list=response['Item']['vol_list']

        try:
            for vol in vol_list:
                    response = table.get_item(
                        Key={
                            'volume_id': vol,
                        }

                        )
                    vol_status=response['Item']['after_type']
                    if (vol_status == 'gp3'):
                            message = message + vol + '\t\t' + account_id + '\t\t\t\t' +'Successful\n'
                    else:
                            message = message + vol + '\t\t' + account_id + '\t\t\t\t' + 'Failed. Please review CloudWatch Logs for details\n'

            message = message + '==============================End of Message ======================================\n'

            response = sns_client.publish(
                    TopicArn=SNS_ARN,   
                    Subject="gp3 upgrade status",
                    Message=message,   
                )
        except ClientError as e:
                print(e.response['Error']['Message'])
    else:
        response = table.put_item(
            Item={
                   'volume_id': 'vol-meta-' + account_id,
                    'vol_list': vol_list,
                    'run_seq': 1,
                }
        ) 

        try:
            for v in volume_iterator:

                if (check_tags(v.tags, v.id)): 
                    response = table.put_item(
                    Item={
                        'volume_id': v.id,
                        'before_type': v.volume_type,
                        'after_type': 'Null',
                        'before_status': v.describe_status(),
                        'size': v.size,
                        'tags': v.tags,
                        'Account ID': account_id,

                        }
                    )

                    try:
                        vol_mod = ec2_client.modify_volume(
                            VolumeId = v.id,
                            VolumeType = 'gp3'

                        )
                    except ClientError as e:
                        print(e.response['Error']['Message'])

        except ClientError as e:
            print(e.response['Error']['Message'])
