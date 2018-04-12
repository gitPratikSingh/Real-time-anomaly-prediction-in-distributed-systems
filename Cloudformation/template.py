import troposphere.ec2 as ec2
import troposphere.cloudformation as cfn
import troposphere.autoscaling as autoscaling
from troposphere.policies import CreationPolicy, ResourceSignal
from troposphere import Parameter, Template, Tags, Ref, Join, Base64
import socket
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--keyname', '-k', help='name of the key for accessing the stack', default="724_keypair")
parser.add_argument('--id', '-i', help='unique time stamp id', default=None, required=False)
args = parser.parse_args()

# Vars
keyname = args.keyname
epoch_time = args.id
template_file = "_".join([epoch_time, "template.json"])
hostname = socket.gethostname()
region = 'us-east-2'
availability_zone = region + 'b'
description = "724 stack created by {} at {}".format(hostname, epoch_time)
cidrs = {
    "vpc": '172.25.0.0/16',
    "public_subnet": '172.25.0.0/17',
    "private_subnet": '172.25.128.0/17',
}

address = {
    "nat": '172.25.0.5',
    "db": '172.25.130.7',
    "web_server": '172.25.130.8',
    "kafka": '172.25.130.9',
    "htm": '172.25.130.10',
    "rubis_client1": '172.25.130.11',
    "rubis_client2": '172.25.130.12',
    "rubis_client3": '172.25.130.13',
    "rubis_client4": '172.25.130.14',
    "rubis_client5": '172.25.130.15',
}

ami_ids = {
    "nat": "ami-f27b5a97",
    "rubis": "ami-ab1a31ce",
    "db": "ami-ab1a31ce",
    "kafka": "ami-ab1a31ce",
    "web_server": "ami-ab1a31ce",
    # "htm": "ami-aad1e0cf",
    "htm": "ami-6e95a50b",
}

t = Template()
t.add_version("2010-09-09")
t.add_description(description)


vpc_cidr = t.add_parameter(Parameter(
    'VPCCIDR',
    Default=cidrs['vpc'],
    Description='The IP address space for this VPC, in CIDR notation',
    Type='String',
))

public_subnet_cidr = t.add_parameter(Parameter(
    'PublicSubnetCidr',
    Type='String',
    Description='Public Subnet CIDR',
    Default=cidrs['public_subnet']
))

private_subnet_cidr = t.add_parameter(Parameter(
    'PrivateSubnetCidr',
    Type='String',
    Description='Private Subnet CIDR',
    Default=cidrs['private_subnet']
))

vpc = t.add_resource(ec2.VPC(
    "VPC",
    CidrBlock=Ref(vpc_cidr),
    InstanceTenancy="default",
    Tags=Tags(
        Name=Ref("AWS::StackName"),
        Creator=hostname
    )
))

public_subnet = t.add_resource(ec2.Subnet(
    'PublicSubnet',
    CidrBlock=Ref(public_subnet_cidr),
    MapPublicIpOnLaunch=True,
    AvailabilityZone=availability_zone,
    VpcId=Ref(vpc),
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "public", "subnet"]),
      )
))

private_subnet = t.add_resource(ec2.Subnet(
    'PrivateSubnet',
    CidrBlock=Ref(private_subnet_cidr),
    MapPublicIpOnLaunch=False,
    AvailabilityZone=availability_zone,
    VpcId=Ref(vpc),
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "private", "subnet"]),
      )
))

igw = t.add_resource(ec2.InternetGateway(
    "InternetGateway",
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "gateway"]),
      )
))

igw_vpc_attachment = t.add_resource(ec2.VPCGatewayAttachment(
    "InternetGatewayAttachment",
    InternetGatewayId=Ref(igw),
    VpcId=Ref(vpc)
))

public_route_table = t.add_resource(ec2.RouteTable(
    "PublicRouteTable",
    VpcId=Ref(vpc),
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "public", "route", "table"])
    )
))

public_route_association = t.add_resource(ec2.SubnetRouteTableAssociation(
    'PublicRouteAssociation',
    SubnetId=Ref(public_subnet),
    RouteTableId=Ref(public_route_table)
))

default_public_route = t.add_resource(ec2.Route(
    'PublicDefaultRoute',
    RouteTableId=Ref(public_route_table),
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId=Ref(igw)
))

private_route_table = t.add_resource(ec2.RouteTable(
    'PrivateRouteTable',
    VpcId=Ref(vpc),
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "private", "route", "table"])
    )
))

private_route_association = t.add_resource(ec2.SubnetRouteTableAssociation(
    'PrivateRouteAssociation',
    SubnetId=Ref(private_subnet),
    RouteTableId=Ref(private_route_table)
))

nat_security_group = t.add_resource(ec2.SecurityGroup(
    'NatSecurityGroup',
    GroupDescription='Nat security group',
    VpcId=Ref(vpc),
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "nat", "security", "group"]),
      ),
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol='-1',
            FromPort=-1,
            ToPort=-1,
            CidrIp='0.0.0.0/0'
        )
    ],
    SecurityGroupEgress=[
        ec2.SecurityGroupRule(
            IpProtocol='-1',
            FromPort=-1,
            ToPort=-1,
            CidrIp='0.0.0.0/0'
        )
    ]
))

nat_instance_metadata = autoscaling.Metadata(
    cfn.Init({
        'config': cfn.InitConfig(
            packages={'yum': {'httpd': []}},
            files=cfn.InitFiles({
                '/etc/cfn/cfn-hup.conf': cfn.InitFile(
                    content=Join('',
                        ['[main]\n',
                         'stack=',
                         Ref('AWS::StackName'),
                         '\n',
                         'region=',
                         Ref('AWS::Region'),
                         '\n',
                        ]),
                    mode='000400',
                    owner='root',
                    group='root'),
                '/etc/cfn/hooks.d/cfn-auto-reloader.conf': cfn.InitFile(
                    content=Join('',
                        ['[cfn-auto-reloader-hook]\n',
                         'triggers=post.update\n',
                         'path=Resources.NatInstance.Metadata.AWS::CloudFormation::Init\n',
                         'action=/opt/aws/bin/cfn-init -v ',
                         '         --stack=',
                         Ref('AWS::StackName'),
                         '         --resource=NatInstance',
                         '         --region=',
                         Ref('AWS::Region'),
                         '\n',
                         'runas=root\n',
                        ]))}),
            services={
                'sysvinit': cfn.InitServices({
                    'httpd': cfn.InitService(
                        enabled=True,
                        ensureRunning=True),
                    'cfn-hup': cfn.InitService(
                        enabled=True,
                        ensureRunning=True,
                        files=[
                            '/etc/cfn/cfn-hup.conf',
                            '/etc/cfn/hooks.d/cfn-auto-reloader.conf'
                        ])})})}))

nat_instance = t.add_resource(ec2.Instance(
    'NatInstance',
    ImageId=ami_ids["nat"],
    InstanceType="t2.micro",
    Metadata=nat_instance_metadata,
    KeyName=keyname,
    SourceDestCheck='false',
    IamInstanceProfile='NatS3Access',   # Ensure this is created before running this template
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            GroupSet=[Ref(nat_security_group)],
            AssociatePublicIpAddress='true',
            DeviceIndex='0',
            PrivateIpAddress=address['nat'],
            DeleteOnTermination='true',
            SubnetId=Ref(public_subnet))],
    UserData=Base64(
        Join(
            '',
            [
                '#!/bin/bash -xe\n',
                'yum update -y aws-cfn-bootstrap\n',
                '/opt/aws/bin/cfn-init -v ',
                '         --stack=',
                Ref('AWS::StackName'),
                '         --resource=NatInstance',
                '         --region=',
                Ref('AWS::Region'),
                '\n',
                'aws --region ', Ref('AWS::Region'), ' s3 cp s3://atambol/keys/nat /home/ec2-user/.ssh/id_rsa\n',
                'aws --region ', Ref('AWS::Region'), ' s3 cp s3://atambol/keys/nat.pub /home/ec2-user/.ssh/id_rsa.pub\n',
                'chmod 400 /home/ec2-user/.ssh/id_rsa /home/ec2-user/.ssh/id_rsa.pub /home/ec2-user/.ssh/authorized_keys\n',
                'chown ec2-user.ec2-user /home/ec2-user/.ssh/id_rsa /home/ec2-user/.ssh/id_rsa.pub /home/ec2-user/.ssh/authorized_keys\n',

                "# Configure iptables\n",
                "/sbin/iptables -t nat -A PREROUTING -p tcp --dport 3030 -j DNAT --to-destination " + address["kafka"] + ":3030\n",
                "/sbin/iptables -t nat -A PREROUTING -p tcp --dport 8080 -j DNAT --to-destination " + address["web_server"] + ":80\n",
                "/sbin/iptables -t nat -A POSTROUTING -o eth0 -s 0.0.0.0/0 -j MASQUERADE\n",
                "/sbin/iptables-save > /etc/sysconfig/iptables\n",
                "# Configure ip forwarding and redirects\n",
                "echo 1 >  /proc/sys/net/ipv4/ip_forward && echo 0 >  /proc/sys/net/ipv4/conf/eth0/send_redirects\n",
                "mkdir -p /etc/sysctl.d/\n",
                "cat <<EOF > /etc/sysctl.d/nat.conf\n",
                "net.ipv4.ip_forward = 1\n",
                "net.ipv4.conf.eth0.send_redirects = 0\n",
                "EOF\n",
                "sysctl -p /etc/sysctl.d/nat.conf\n",

                'pip install kafka-python\n',
                'wget https://raw.githubusercontent.com/atambol/Real-time-anomaly-prediction-in-distributed-systems/master/StreamingApp/StreamEngine/StreamAggregator.py -P /home/ec2-user\n',
                #'wget https://raw.githubusercontent.com/atambol/Real-time-anomaly-prediction-in-distributed-systems/master/StreamingApp/StreamEngine/DataCollector.py -P /home/ec2-user\n',
                'chown ec2-user.ec2-user /home/ec2-user/*.py\n',
                # 'python /home/ec2-user/StreamAggregator.py & \n',
                '/opt/aws/bin/cfn-signal -e $?',
                '         --stack=',
                Ref('AWS::StackName'),
                '         --resource=NatInstance',
                '         --region=',
                Ref('AWS::Region'),
                '\n',
            ])),
    CreationPolicy=CreationPolicy(
        ResourceSignal=ResourceSignal(
            Count=1,
            Timeout='PT5M')),
    DependsOn=["InternetGatewayAttachment"],
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "Nat"]))
))

default_private_route = t.add_resource(ec2.Route(
    'PrivateDefaultRoute',
    RouteTableId=Ref(private_route_table),
    DestinationCidrBlock='0.0.0.0/0',
    InstanceId=Ref(nat_instance),
    DependsOn=["NatInstance"]
))

instance_security_group = t.add_resource(ec2.SecurityGroup(
    'InstanceSecurityGroup',
    GroupDescription='Instance security group',
    VpcId=Ref(vpc),
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "instance", "security", "group"]),
      ),
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol='-1',
            FromPort=-1,
            ToPort=-1,
            CidrIp='0.0.0.0/0'
        )
    ],
    SecurityGroupEgress=[
        ec2.SecurityGroupRule(
            IpProtocol='-1',
            FromPort=-1,
            ToPort=-1,
            CidrIp='0.0.0.0/0'
        )
    ]
))


def get_instance_metadata(instance_name):
    return autoscaling.Metadata(
        cfn.Init({
            'config': cfn.InitConfig(
                packages={'yum': {'httpd': []}},
                files=cfn.InitFiles({
                    '/etc/cfn/cfn-hup.conf': cfn.InitFile(
                        content=Join('',
                            ['[main]\n',
                             'stack=',
                             Ref('AWS::StackName'),
                             '\n',
                             'region=',
                             Ref('AWS::Region'),
                             '\n',
                            ]),
                        mode='000400',
                        owner='root',
                        group='root'),
                    '/etc/cfn/hooks.d/cfn-auto-reloader.conf': cfn.InitFile(
                        content=Join('',
                            ['[cfn-auto-reloader-hook]\n',
                             'triggers=post.update\n',
                             'path=Resources.',
                             instance_name,
                             '.Metadata.AWS::CloudFormation::Init\n',
                             'action=/opt/aws/bin/cfn-init -v ',
                             '         --stack=',
                             Ref('AWS::StackName'),
                             '         --resource=',
                             instance_name,
                             '         --region=',
                             Ref('AWS::Region'),
                             '\n',
                             'runas=root\n',
                            ]))}),
                services={
                    'sysvinit': cfn.InitServices({
                        'httpd': cfn.InitService(
                            enabled=True,
                            ensureRunning=True),
                        'cfn-hup': cfn.InitService(
                            enabled=True,
                            ensureRunning=True,
                            files=[
                                '/etc/cfn/cfn-hup.conf',
                                '/etc/cfn/hooks.d/cfn-auto-reloader.conf'
                            ])})})}))


htm_instance = t.add_resource(ec2.Instance(
    'HTM',
    ImageId=ami_ids["htm"],
    InstanceType="t2.small",
    KeyName=keyname,
    SourceDestCheck='true',
    # IamInstanceProfile='NatS3Access',
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            GroupSet=[Ref(instance_security_group)],
            PrivateIpAddress=address['htm'],
            DeviceIndex='0',
            DeleteOnTermination='true',
            SubnetId=Ref(private_subnet))],
    DependsOn=["PrivateDefaultRoute"],
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "HTM"]))
))

kafka_instance = t.add_resource(ec2.Instance(
    'KafkaInstance',
    ImageId=ami_ids["kafka"],
    InstanceType="t2.large",
    Metadata=get_instance_metadata("KafkaInstance"),
    KeyName=keyname,
    SourceDestCheck='true',
    IamInstanceProfile='NatS3Access',
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            GroupSet=[Ref(instance_security_group)],
            PrivateIpAddress=address['kafka'],
            DeviceIndex='0',
            DeleteOnTermination='true',
            SubnetId=Ref(private_subnet))],
    UserData=Base64(
        Join(
            '',
            [
                '#!/bin/bash -xe\n',
                'yum update -y aws-cfn-bootstrap\n',
                '/opt/aws/bin/cfn-init -v ',
                '         --stack=',
                Ref('AWS::StackName'),
                '         --resource=KafkaInstance',
                '         --region=',
                Ref('AWS::Region'),
                '\n',

                'aws --region ', Ref('AWS::Region'), ' s3 cp s3://atambol/keys/kafka /home/ec2-user/.ssh/id_rsa\n',
                'aws --region ', Ref('AWS::Region'), ' s3 cp s3://atambol/keys/kafka.pub /home/ec2-user/.ssh/id_rsa.pub\n',
                'aws --region ', Ref('AWS::Region'), ' s3 cp s3://atambol/keys/authorized_keys /home/ec2-user/.ssh/authorized_keys\n',
                'chmod 400 /home/ec2-user/.ssh/id_rsa /home/ec2-user/.ssh/id_rsa.pub /home/ec2-user/.ssh/authorized_keys\n',
                'chown ec2-user.ec2-user /home/ec2-user/.ssh/id_rsa /home/ec2-user/.ssh/id_rsa.pub /home/ec2-user/.ssh/authorized_keys\n',

                'yum update -y\n',
                'yum install docker -y\n',
                'service docker start\n',
                'sudo docker run --rm -it -d -p 2181:2181 -p 3030:3030 -p 8081:8081 -p 8082:8082 -p 8083:8083 -p 9092:9092 -e ADV_HOST=172.25.130.9 landoop/fast-data-dev\n',
                '/opt/aws/bin/cfn-signal -e $? ',

                '         --stack=',
                Ref('AWS::StackName'),
                '         --resource=KafkaInstance',
                '         --region=',
                Ref('AWS::Region'),
                '\n',
            ])),
    CreationPolicy=CreationPolicy(
        ResourceSignal=ResourceSignal(
            Count=1,
            Timeout='PT5M')),
    DependsOn=["PrivateDefaultRoute"],
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "Kafka"]))
))

db_instance = t.add_resource(ec2.Instance(
    'DBInstance',
    ImageId=ami_ids["db"],
    InstanceType="t2.small",
    Metadata=get_instance_metadata("DBInstance"),
    IamInstanceProfile='NatS3Access',
    KeyName=keyname,
    SourceDestCheck='true',
    BlockDeviceMappings=[
        ec2.BlockDeviceMapping(
            DeviceName="/dev/xvda",
            Ebs=ec2.EBSBlockDevice(
                VolumeSize="15"
            )
        ),
    ],
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            GroupSet=[Ref(instance_security_group)],
            PrivateIpAddress=address['db'],
            DeviceIndex='0',
            DeleteOnTermination='true',
            SubnetId=Ref(private_subnet))],
    UserData=Base64(
        Join(
            '',
            [
                '#!/bin/bash -xe\n',
                'yum update -y aws-cfn-bootstrap\n',
                '/opt/aws/bin/cfn-init -v ',
                '         --stack=',
                Ref('AWS::StackName'),
                '         --resource=DBInstance',
                '         --region=',
                Ref('AWS::Region'),
                '\n',

                'aws --region ', Ref('AWS::Region'), ' s3 cp s3://atambol/keys/db /home/ec2-user/.ssh/id_rsa\n',
                'aws --region ', Ref('AWS::Region'),
                ' s3 cp s3://atambol/keys/db.pub /home/ec2-user/.ssh/id_rsa.pub\n',
                'aws --region ', Ref('AWS::Region'),
                ' s3 cp s3://atambol/keys/authorized_keys /home/ec2-user/.ssh/authorized_keys\n',
                'chmod 400 /home/ec2-user/.ssh/id_rsa /home/ec2-user/.ssh/id_rsa.pub /home/ec2-user/.ssh/authorized_keys\n',
                'chown ec2-user.ec2-user /home/ec2-user/.ssh/id_rsa /home/ec2-user/.ssh/id_rsa.pub /home/ec2-user/.ssh/authorized_keys\n',

                'yum update -y\n',
                'yum remove -y php-pdo-5.3.29-1.8.amzn1.x86_64 php-common-5.3.29-1.8.amzn1.x86_64 httpd-2.2.34-1.16.amzn1.x86_64 httpd-tools-2.2.34-1.16.amzn1.x86_64 php-5.3.29-1.8.amzn1.x86_64 php-process-5.3.29-1.8.amzn1.x86_64 php-xml-5.3.29-1.8.amzn1.x86_64 php-cli-5.3.29-1.8.amzn1.x86_64 php-gd-5.3.29-1.8.amzn1.x86_64\n',
                'yum install -y mysql56-server php70-mysqlnd gcc git\n',
                'pip install psutil kafka-python\n',
                'service mysqld start\n',
                'mysql_secure_installation << EOL\n',
                '\n',
                'n\n',
                'Y\n',
                'Y\n',
                'Y\n',
                'Y\n',
                'EOL\n',
                'chkconfig mysqld on\n',
                'git clone https://github.com/atambol/RUBiS.git\n',
                'export RUBIS_HOME=`readlink -f RUBiS`\n',
                'cd $RUBIS_HOME/database\n',
                'aws --region ', Ref('AWS::Region'),
                ' s3 cp s3://atambol/keys/rubis_backup.sql.gz rubis_backup.sql.gz\n',
                'chmod 644 rubis_backup.sql.gz\n',
                'gunzip rubis_backup.sql.gz\n',

                'mysql -u root --execute="CREATE DATABASE rubis;"\n',
                'mysql -u root --execute="GRANT ALL PRIVILEGES ON *.* TO \'root\'@\'%\' WITH GRANT OPTION;"\n',
                'mysql -uroot rubis < rubis.sql\n',
                'mysql -uroot rubis < categories.sql\n',
                'mysql -uroot rubis < regions.sql\n',
                'mysql -uroot rubis < rubis_backup.sql\n',

                '/opt/aws/bin/cfn-signal -e $? ',
                '         --stack=',
                Ref('AWS::StackName'),
                '         --resource=DBInstance',
                '         --region=',
                Ref('AWS::Region'),
                '\n',
            ])),
    CreationPolicy=CreationPolicy(
        ResourceSignal=ResourceSignal(
            Count=1,
            Timeout='PT15M')),
    DependsOn=["PrivateDefaultRoute"],
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "DB"]))
))

web_server_instance = t.add_resource(ec2.Instance(
    'WebServerInstance',
    ImageId=ami_ids["web_server"],
    InstanceType="t2.micro",
    Metadata=get_instance_metadata("WebServerInstance"),
    IamInstanceProfile='NatS3Access',
    KeyName=keyname,
    SourceDestCheck='true',
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            GroupSet=[Ref(instance_security_group)],
            PrivateIpAddress=address['web_server'],
            DeviceIndex='0',
            DeleteOnTermination='true',
            SubnetId=Ref(private_subnet))],
    UserData=Base64(
        Join(
            '',
            [
                '#!/bin/bash -xe\n',
                'yum update -y aws-cfn-bootstrap\n',
                '/opt/aws/bin/cfn-init -v ',
                '         --stack=',
                Ref('AWS::StackName'),
                '         --resource=WebServerInstance',
                '         --region=',
                Ref('AWS::Region'),
                '\n',

                'aws --region ', Ref('AWS::Region'), ' s3 cp s3://atambol/keys/web_server /home/ec2-user/.ssh/id_rsa\n',
                'aws --region ', Ref('AWS::Region'),
                ' s3 cp s3://atambol/keys/web_server.pub /home/ec2-user/.ssh/id_rsa.pub\n',
                'aws --region ', Ref('AWS::Region'),
                ' s3 cp s3://atambol/keys/authorized_keys /home/ec2-user/.ssh/authorized_keys\n',
                'chmod 400 /home/ec2-user/.ssh/id_rsa /home/ec2-user/.ssh/id_rsa.pub /home/ec2-user/.ssh/authorized_keys\n',
                'chown ec2-user.ec2-user /home/ec2-user/.ssh/id_rsa /home/ec2-user/.ssh/id_rsa.pub /home/ec2-user/.ssh/authorized_keys\n',

                'yum update -y\n',
                'yum remove -y php-pdo-5.3.29-1.8.amzn1.x86_64 php-common-5.3.29-1.8.amzn1.x86_64 httpd-2.2.34-1.16.amzn1.x86_64 httpd-tools-2.2.34-1.16.amzn1.x86_64 php-5.3.29-1.8.amzn1.x86_64 php-process-5.3.29-1.8.amzn1.x86_64 php-xml-5.3.29-1.8.amzn1.x86_64 php-cli-5.3.29-1.8.amzn1.x86_64 php-gd-5.3.29-1.8.amzn1.x86_64\n',
                'yum install -y httpd24 php70 php70-mysqlnd gcc git\n',
                'pip install psutil kafka-python\n',
                'service httpd start\n',
                'chkconfig httpd on\n',
                '#chkconfig --list httpd\n',
                'usermod -a -G apache ec2-user\n',
                'chown -R ec2-user:apache /var/www\n',
                'chmod 2775 /var/www\n',
                'find /var/www -type d -exec sudo chmod 2775 {} \;\n',
                'find /var/www -type f -exec sudo chmod 0664 {} \;\n',
                'git clone https://github.com/atambol/RUBiS.git\n',
                'export RUBIS_HOME=`readlink -f RUBiS`\n',
                'cp -r $RUBIS_HOME/PHP/ /var/www/html/\n',

                'wget https://raw.githubusercontent.com/atambol/Real-time-anomaly-prediction-in-distributed-systems/master/StreamingApp/StreamEngine/MetricsKafkaProducer.py -P /home/ec2-user/\n',
                'chown ec2-user.ec2-user /home/ec2-user/MetricsKafkaProducer.py\n',
                'python /home/ec2-user/MetricsKafkaProducer.py & \n',

                '/opt/aws/bin/cfn-signal -e $? ',
                '         --stack=',
                Ref('AWS::StackName'),
                '         --resource=WebServerInstance',
                '         --region=',
                Ref('AWS::Region'),
                '\n',
            ])),
    CreationPolicy=CreationPolicy(
        ResourceSignal=ResourceSignal(
            Count=1,
            Timeout='PT5M')),
    DependsOn=["PrivateDefaultRoute"],
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "WebServer"]))
))

for i in range(1, 6):
    key = "rubis_client" + str(i)
    instance_name = "RubisInstance" + str(i)
    t.add_resource(ec2.Instance(
        instance_name,
        ImageId=ami_ids['rubis'],
        InstanceType="t2.micro",
        Metadata=get_instance_metadata(instance_name),
        KeyName=keyname,
        SourceDestCheck='true',
        IamInstanceProfile='NatS3Access',
        NetworkInterfaces=[
            ec2.NetworkInterfaceProperty(
                GroupSet=[Ref(instance_security_group)],
                PrivateIpAddress=address[key],
                DeviceIndex='0',
                DeleteOnTermination='true',
                SubnetId=Ref(private_subnet))],
        UserData=Base64(
            Join(
                '',
                [
                    '#!/bin/bash -xe\n',
                    'yum update -y aws-cfn-bootstrap\n',
                    '/opt/aws/bin/cfn-init -v ',
                    '         --stack=',
                    Ref('AWS::StackName'),
                    '         --resource=' + instance_name,
                    '         --region=',
                    Ref('AWS::Region'),
                    '\n',

                    'aws --region ', Ref('AWS::Region'), ' s3 cp s3://atambol/keys/rubis', i, ' /home/ec2-user/.ssh/id_rsa\n',
                    'aws --region ', Ref('AWS::Region'),
                    ' s3 cp s3://atambol/keys/rubis', i, ' /home/ec2-user/.ssh/id_rsa.pub\n',
                    'aws --region ', Ref('AWS::Region'),
                    ' s3 cp s3://atambol/keys/authorized_keys /home/ec2-user/.ssh/authorized_keys\n',
                    'chmod 400 /home/ec2-user/.ssh/id_rsa /home/ec2-user/.ssh/id_rsa.pub /home/ec2-user/.ssh/authorized_keys\n',
                    'chown ec2-user.ec2-user /home/ec2-user/.ssh/id_rsa /home/ec2-user/.ssh/id_rsa.pub /home/ec2-user/.ssh/authorized_keys\n',

                    'yum update -y\n',
                    'yum remove -y php-pdo-5.3.29-1.8.amzn1.x86_64 php-common-5.3.29-1.8.amzn1.x86_64 httpd-2.2.34-1.16.amzn1.x86_64 httpd-tools-2.2.34-1.16.amzn1.x86_64 php-5.3.29-1.8.amzn1.x86_64 php-process-5.3.29-1.8.amzn1.x86_64 php-xml-5.3.29-1.8.amzn1.x86_64 php-cli-5.3.29-1.8.amzn1.x86_64 php-gd-5.3.29-1.8.amzn1.x86_64\n',
                    'yum install git gcc java-1.8.0-openjdk-devel.x86_64 -y\n',
                    'pip install psutil\n',
                    'git clone https://github.com/atambol/RUBiS.git\n',
                    'export JAVA_HOME="/usr/lib/jvm/java-1.8.0-openjdk"\n',
                    'export RUBIS_HOME=`readlink -f RUBiS`\n',
                    'cd $RUBIS_HOME/Client\n',
                    #'python generateProperties.py -d ', address["db"], ' -p ', address["web_server"], '\n',
                    'export PATH="$JAVA_HOME/bin:$PATH"\n',
                    'echo "export JAVA_HOME=\"/usr/lib/jvm/java-1.8.0-openjdk\"" >> /etc/environment\n',
                    'echo "export PATH=\"$JAVA_HOME/bin:$PATH\"" >> /etc/environment\n',
                    'chown ec2-user.ec2-user /RUBiS -R\n',
                    'make client\n',
                    'make emulator &\n',

                    '/opt/aws/bin/cfn-signal -e $? ',
                    '         --stack=',
                    Ref('AWS::StackName'),
                    '         --resource=' + instance_name,
                    '         --region=',
                    Ref('AWS::Region'),
                    '\n',
                ])),
        CreationPolicy=CreationPolicy(
            ResourceSignal=ResourceSignal(
                Count=1,
                Timeout='PT5M')),
        DependsOn=["DBInstance"],
        Tags=Tags(
            Name=Join("_", [Ref("AWS::StackName"), instance_name]))
    ))

# Generate a template
with open(template_file, "w") as f:
    f.writelines(t.to_json())
