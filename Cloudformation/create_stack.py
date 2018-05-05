# Author: Anirudha Tambolkar
# Description: Creates stack on AWS from the template generated using template.py

import boto3
import subprocess
import time
import os


epoch_time = str(int(time.time()))
stackname = "-".join(["Test", epoch_time])
template_name = "_".join([epoch_time, "template.json"])
key = "templates"
bucket = "atambol"
region = "us-east-2"
template_url = "/".join(["https://s3." + region + ".amazonaws.com", bucket, key, template_name])

# Create Template
p = subprocess.Popen(['python', 'template.py', '-i', epoch_time], stdout=subprocess.PIPE)
out, err = p.communicate()
if p.returncode is not 0:
    print(out, err)
else:
    # Upload template to s3
    s3 = boto3.client('s3')
    s3.upload_file(
        Filename=template_name,
        Bucket=bucket,
        Key="/".join([key, template_name])
    )

    # Create stack
    cfn = boto3.client('cloudformation')
    response = cfn.create_stack(
        StackName=stackname,
        TemplateURL=template_url,
        OnFailure="DO_NOTHING",
    )

    # Delete template
    s3.delete_object(
        Bucket=bucket,
        Key="/".join([key, template_name])
    )

    os.rename(template_name, "template.json")