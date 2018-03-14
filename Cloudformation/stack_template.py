import troposphere.cloudformation as cfn
import troposphere.ec2 as ec2
from troposphere import Template, Tags, Ref, Join
import socket
import time

# Vars
epoch_time = str(int(time.time()))
hostname = socket.gethostname()
description = "_".join(["724", hostname, epoch_time])
address = {
    "subnet": "172.25.0.0/16",
    "kafka_ips": ["172.25.1.1"],
    "flink_ips": ["172.25.2.1"],
    "rubis_ips": ["172.25.3.1"]
}

# Templating begins
t = Template()
t.add_version("2010-09-09")
t.add_description(description)

# Create a VPC
vpc = t.add_resource(
    ec2.VPC(
        "VPC",
        CidrBlock=address["subnet"],
        InstanceTenancy="default",
        EnableDnsSupport=True,
        EnableDnsHostnames=False,
        Tags=Tags(
            Name=Ref("AWS::StackName"),
            Creator=hostname
        )
    )
)

# Create GW
igw = t.add_resource(
    ec2.InternetGateway(
        "InternetGateway",
        Tags=Tags(
            Name=Join("_", [Ref("AWS::StackName"), "gateway"]),
          )
    )
)

# Associate GW with VPC
igw_vpc_attachment = t.add_resource(ec2.VPCGatewayAttachment(
        "InternetGatewayAttachment",
        InternetGatewayId=Ref(igw),
        VpcId=Ref(vpc)
    )
)

# Create public routing table
pub_rtt = t.add_resource(ec2.RouteTable(
        "PublicRouteTable",
        VpcId=Ref(vpc),
        Tags=Tags(
            Name=Join("_", [Ref("AWS::StackName"), "public", "routing", "table"]),
        )
    )
)

# Create public route
pub_rt = t.add_resource(ec2.Route(
      "RouteToInternet",
      DestinationCidrBlock="0.0.0.0/0",
      GatewayId=Ref(igw),
      RouteTableId=Ref(pub_rtt),
      DependsOn=igw_vpc_attachment.title
    )
)

# Create private routing table
prv_rtt = t.add_resource(ec2.RouteTable(
        "PrivateRouteTable",
        VpcId=Ref(vpc),
        Tags=Tags(
            Name=Join("_", [Ref("AWS::StackName"), "private", "routing", "table"]),
        )
    )
)

# Private Subnet
prv_subnet = t.add_resource(ec2.Subnet(
        "StackPrivateSubnet",
        AvailabilityZone=Join("", [Ref("AWS::Region"), "a"]),
        CidrBlock=address["subnet"],
        MapPublicIpOnLaunch=False,
        VpcId=Ref(vpc),
        Tags=Tags(
            Name=Join("_", [Ref("AWS::StackName"), "private", "subnet"]),
        )
    )
)

# Associate subnet with routing table
prv_subnet_prv_rtt_association = t.add_resource(ec2.SubnetRouteTableAssociation(
  "PrivateSubnetARouteTable",
  RouteTableId=Ref(prv_rtt),
  SubnetId=Ref(prv_subnet)
))

# Generate a template
with open("template.json", "w") as f:
    f.writelines(t.to_json())