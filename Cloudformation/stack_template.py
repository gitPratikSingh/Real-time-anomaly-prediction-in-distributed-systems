import troposphere.ec2 as ec2
from troposphere import Parameter, Template, Tags, Ref, Join, GetAtt
import socket
import time

# Vars
keyname = "724_keypair"
epoch_time = str(int(time.time()))
hostname = socket.gethostname()
description = "_".join(["724", hostname, epoch_time])
address = {
    "vpc_cidr": '172.25.0.0/16',
    "public_subnet_cidr": '172.25.0.0/17',
    "private_subnet_cidr": '172.25.128.0/17',
    "kafka": ["172.25.128.1"],
    "spark": ["172.25.129.1"],
    "rubis": ["172.25.130.1"]
}

ami_ids = {
    "nat": "ami-92a6fef7"
}

t = Template()
t.add_version("2010-09-09")
t.add_description(description)


vpc_cidr = t.add_parameter(Parameter(
    'VPCCIDR',
    Default=address['vpc_cidr'],
    Description='The IP address space for this VPC, in CIDR notation',
    Type='String',
))

public_subnet_cidr = t.add_parameter(Parameter(
    'PublicSubnetCidr',
    Type='String',
    Description='Public Subnet CIDR',
    Default=address['public_subnet_cidr']
))

private_subnet_cidr = t.add_parameter(Parameter(
    'PrivateSubnetCidr',
    Type='String',
    Description='Public Subnet CIDR',
    Default=address['private_subnet_cidr']
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
    VpcId=Ref(vpc),
))

private_subnet = t.add_resource(ec2.Subnet(
    'PrivateSubnet',
    CidrBlock=Ref(private_subnet_cidr),
    MapPublicIpOnLaunch=False,
    VpcId=Ref(vpc),
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
    RouteTableId=Ref(public_route_table),
))

default_public_route = t.add_resource(ec2.Route(
    'PublicDefaultRoute',
    RouteTableId=Ref(public_route_table),
    DestinationCidrBlock='0.0.0.0/0',
    GatewayId=Ref(igw),
))

private_route_table = t.add_resource(ec2.RouteTable(
    'PrivateRouteTable',
    VpcId=Ref(vpc),
))

private_route_association = t.add_resource(ec2.SubnetRouteTableAssociation(
    'PrivateRouteAssociation',
    SubnetId=Ref(private_subnet),
    RouteTableId=Ref(private_route_table),
))

eip = t.add_resource(ec2.EIP(
    'NatEip',
    Domain="vpc",
))

nat_security_group = t.add_resource(ec2.SecurityGroup(
    'SecurityGroup',
    GroupDescription='Nat security group',
    VpcId=Ref(vpc),
    SecurityGroupIngress=[
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort=22,
            ToPort=22,
            CidrIp='0.0.0.0/0'
        ),
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort=80,
            ToPort=80,
            CidrIp=address['private_subnet_cidr']
        ),
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort=443,
            ToPort=443,
            CidrIp=address['private_subnet_cidr']
        )
    ],
    SecurityGroupEgress=[
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort=443,
            ToPort=443,
            CidrIp='0.0.0.0/0'
        ),
        ec2.SecurityGroupRule(
            IpProtocol='tcp',
            FromPort=80,
            ToPort=80,
            CidrIp='0.0.0.0/0'
        )
    ]
))

nat_instance = t.add_resource(ec2.Instance(
    'NatInstance',
    ImageId=ami_ids["nat"],
    InstanceType="t2.micro",
    KeyName=keyname,
    NetworkInterfaces=[
        ec2.NetworkInterfaceProperty(
            GroupSet=[Ref(nat_security_group)],
            AssociatePublicIpAddress='true',
            DeviceIndex='0',
            DeleteOnTermination='true',
            SubnetId=Ref(public_subnet))],
    # UserData=Base64(
    #     Join(
    #         '',
    #         [
    #             '#!/bin/bash -xe\n',
    #             'yum update -y aws-cfn-bootstrap\n',
    #             '/opt/aws/bin/cfn-init -v ',
    #             '         --stack ',
    #             Ref('AWS::StackName'),
    #             '         --resource WebServerInstance ',
    #             '         --region ',
    #             Ref('AWS::Region'),
    #             '\n',
    #             '/opt/aws/bin/cfn-signal -e $? ',
    #             '         --stack ',
    #             Ref('AWS::StackName'),
    #             '         --resource WebServerInstance ',
    #             '         --region ',
    #             Ref('AWS::Region'),
    #             '\n',
    #         ])),
    Tags=Tags(
        Name=Join("_", [Ref("AWS::StackName"), "Nat"]))
))

# Generate a template
with open("template.json", "w") as f:
    f.writelines(t.to_json())
