#!/usr/bin/env python
#
#
# awsclideploy.py
#
# Yanming Xiao
#
#
# Run mode:
#   $ ./awsclideploy.py { build | delete } {deployment.ini}
#
# Debug mode:
#   $ python -m pudb.run awsclideploy.py { build | delete } {deployment.ini}
#
#
import sys
import os
import re
import yaml
import json
import time
import datetime
import shutil
import commands
#
import pprint


#
# supportive functions
#
def PrepareTemplate(command, subcommand):
    templateFileName = _deployment_['control']['templatesubdir'] + '/' + subcommand + '.template'
    #json_data = None
    if not os.path.exists(templateFileName):
       cmd = 'aws ' + command + ' ' + subcommand + ' --generate-cli-skeleton > ' + templateFileName
       ExecShellCommand(cmd, 'generate template for ' + subcommand) 
    #f_json = open(templateFileName, 'r')
    #json_data = json.load(f_json)
    #f_json.close()
    #return json_data


def PrepareInput(command, subcommand, json_data):
    inputFileName = _deployment_['control']['templatesubdir'] + '/' + subcommand + '.input'
    f_json = open(inputFileName, 'w')
    json.dump(json_data, f_json)
    f_json.close()


def Run_subcommand(command, subcommand, jqexpression):
    cmd = 'jq ' + jqexpression + ' < ./templates/' + subcommand + '.template > ./templates/' + subcommand + '.input'
    ExecShellCommand(cmd, 'generate .input for ' + subcommand)
    cmd = 'aws ' + command + ' ' + subcommand + ' --cli-input-json file://./templates/' + subcommand + '.input > ./templates/' + subcommand + '.output'
    ExecShellCommand(cmd, 'run subcommand ' + subcommand)


def Run_subcommand_inputfile(command, subcommand):
    inputFileName = _deployment_['control']['templatesubdir'] + '/' + subcommand + '.input'
    cmd = 'aws ' + command + ' ' + subcommand + ' --cli-input-json file://' + inputFileName
    ExecShellCommand(cmd, 'run subcommand ' + subcommand)


def get_vpc_id_from_output(): 
    cmd = 'jq ".Vpc.VpcId" ./templates/create-vpc.output | sed -e \'s/"//g\''
    vpc_id = ExecShellCommand(cmd, 'get vpc_id')
    return vpc_id


def get_vpc_id():
    #cmd = 'jq ".Vpc.VpcId" ./templates/create-vpc.output | sed -e \'s/"//g\''
    cmd = 'aws ec2 describe-vpcs --filters ' \
          + ' "Name=tag:Name,Values=' + _deployment_['ec2_vpc']['Name'] + '"' \
          + ' "Name=tag:Componment,Values=' + _deployment_['common']['Componment'] + '"' \
          + ' "Name=tag:Version,Values=' + _deployment_['common']['Version'] + '"' \
          + ' "Name=tag:VpcName,Values=' + _deployment_['common']['VpcName'] + '"' \
          + ' --query "Vpcs[*].VpcId" --output text'
    vpc_id = ExecShellCommand(cmd, 'get vpc_id')
    return vpc_id


def get_igw_id():
    #cmd = 'jq ".InternetGateway.InternetGatewayId" ./templates/create-internet-gateway.output | sed -e \'s/"//g\''
    cmd = 'aws ec2 describe-internet-gateways --filters ' \
          + ' "Name=tag:Name,Values=' + _deployment_['ec2_vpc_igw']['Name'] + '"' \
          + ' "Name=tag:Componment,Values=' + _deployment_['common']['Componment'] + '"' \
          + ' "Name=tag:Version,Values=' + _deployment_['common']['Version'] + '"' \
          + ' "Name=tag:VpcName,Values=' + _deployment_['common']['VpcName'] + '"' \
          + ' --query "InternetGateways[*].InternetGatewayId" --output text'
    igw_id = ExecShellCommand(cmd, 'get igw_id')
    return igw_id


def get_igw_id_from_output():
    cmd = 'jq ".InternetGateway.InternetGatewayId" ./templates/create-internet-gateway.output | sed -e \'s/"//g\''
    igw_id = ExecShellCommand(cmd, 'get igw_id')
    return igw_id


def get_subnet_id():
    cmd = 'jq ".Subnet.SubnetId" ./templates/create-subnet.output | sed -e \'s/"//g\''
    subnet_id = ExecShellCommand(cmd, 'get subnet_id') 
    return subnet_id


def get_security_group_id(vpc_id):
    cmd = 'aws ec2 describe-security-groups --filters "Name=vpc-id,Values=' + vpc_id + '" --query "SecurityGroups[*].GroupId" --output text'
    security_group_id = ExecShellCommand(cmd, 'get security_group_id')
    return security_group_id


def get_PolicyARN():
    cmd = 'jq ".PolicyARN" ./templates/put-scaling-policy.output | sed -e \'s/"//g\''
    PolicyARN = ExecShellCommand(cmd, 'get vpc_id')
    return PolicyARN


def get_cluster_endpoint(cluster_identifier):
    cmd = 'aws rds describe-db-clusters --db-cluster-identifier ' + cluster_identifier + ' --query "DBClusters[*].Endpoint" --output text'
    cluster_endpoint = ExecShellCommand(cmd, 'get cluster_endpoint')
    return cluster_endpoint


def tag_resource(resource_id, Name):
    cmd = 'aws ec2 create-tags --resources ' +  resource_id \
          + ' --tags \'[{"Key":"Name","Value":"' + Name \
          + '"},{"Key":"VpcName","Value":"' + _deployment_['common']['VpcName'] \
          + '"},{"Key":"Version","Value":"' + _deployment_['common']['Version'] \
          + '"},{"Key":"Componment","Value":"' + _deployment_['common']['Componment'] + '"}]\''
    ExecShellCommand(cmd, 'tags the resource')


def set_security_group_rules(security_group_id, direction):
    if _deployment_['ec2_vpc'][direction] != None:
        for rule in _deployment_['ec2_vpc'][direction]:
            if direction == 'InBoundRules':
                cmd = 'aws ec2 authorize-security-group-ingress --group-id ' + security_group_id \
                    + ' --protocol ' + rule['protocol'] \
                    + ' --port ' + rule['port'] \
                    + ' --cidr ' + rule['cidr'] 
            elif direction == 'OutBoundRules':
                cmd = 'aws ec2 authorize-security-group-engress --group-id ' + security_group_id \
                    + ' --protocol ' + rule['protocol'] \
                    + ' --port ' + rule['port'] \
                    + ' --cidr ' + rule['cidr'] 
            #print cmd
            ExecShellCommand(cmd, 'tags the resource')
            Sleep(60)


#
# [ec2_vpc]
#
def build_vpc():
    vpc_id = get_vpc_id()
    if vpc_id == '':
        PrepareTemplate('ec2', 'create-vpc')
        jqexpression = '\'.DryRun = false | .CidrBlock = "' + _deployment_['ec2_vpc']['CidrBlock'] + '" | .InstanceTenancy = "default"\''
        Run_subcommand('ec2', 'create-vpc', jqexpression)
        Sleep(60)
        vpc_id = get_vpc_id_from_output()
        # tag VPC
        tag_resource(vpc_id, _deployment_['ec2_vpc']['Name'])
        # tag Security Group of the VPC
        security_group_id = get_security_group_id(vpc_id)    
        tag_resource(security_group_id, _deployment_['ec2_vpc']['SecurityGroupName'])
        # set inbound rules for the VPC
        set_security_group_rules(security_group_id, 'InBoundRules')
        # set outbound rules for the VPC
        set_security_group_rules(security_group_id, 'OutBoundRules')


def delete_vpc():
    vpc_id = get_vpc_id()
    cmd = 'aws ec2 delete-vpc --vpc-id ' + vpc_id
    ExecShellCommand(cmd, 'delete vpc')    


#
# [ec2_vpc_igw]
#
def build_igw():
    PrepareTemplate('ec2','create-internet-gateway')
    # create igw
    Run_subcommand('ec2','create-internet-gateway', '\'.DryRun = false\'')
    Sleep(60)
    igw_id = get_igw_id_from_output()
    # tag igw
    tag_resource(igw_id, _deployment_['ec2_vpc_igw']['Name'])
    vpc_id = get_vpc_id()
    # attach igw
    cmd = 'aws ec2 attach-internet-gateway --internet-gateway-id ' + igw_id + ' --vpc-id ' + vpc_id
    ExecShellCommand(cmd, 'attach IGW')
    #security_group_id = get_security_group_id(vpc_id)
    

#
#
def delete_igw():
    igw_id = get_igw_id()
    vpc_id = get_vpc_id()

    # detach IGW
    cmd = 'aws ec2 detach-internet-gateway --internet-gateway-id ' + igw_id + ' --vpc-id ' + vpc_id
    ExecShellCommand(cmd, 'detach IGW')
    # delete IGW
    cmd = 'aws ec2 delete-internet-gateway --internet-gateway-id ' + igw_id
    ExecShellCommand(cmd, 'delete IGW')


#
# [ec2_vpc_subnet]
#
def build_subnets():
    PrepareTemplate('ec2','create-subnet')
    vpc_id = get_vpc_id()    
    for i in range(_deployment_['ec2_vpc_subnet']['count_of_subnets']):
        jqexpression = '\'.DryRun = false | .VpcId = "' + vpc_id \
                + '" | .CidrBlock = "' + _deployment_['ec2_vpc_subnet']['CidrBlock'][i] \
                + '" | .AvailabilityZone = "' + _deployment_['ec2_vpc_subnet']['deployzone'][i] + '"\'' 
        # print 'jqexpression =' + jqexpression
        Run_subcommand('ec2','create-subnet', jqexpression)
        Sleep(60)
        subnet_id = get_subnet_id()
        tag_resource(subnet_id, _deployment_['ec2_vpc_subnet']['Name'][i])


def get_subnet_id_by_Name(name):
    cmd = 'aws ec2 describe-subnets --filters "Name=tag:Name,Values=' + name + '" --query "Subnets[*].SubnetId" --output text'
    subnet_id = ExecShellCommand(cmd, 'get subnet id by name')
    return subnet_id


def get_ami_id_by_Name(name):
    cmd = 'aws ec2 describe-images --filters "Name=tag:Name,Values='+ name + '" --query "Images[*].ImageId" --output text'
    ami_id = ExecShellCommand(cmd, 'get ami id by name')
    return ami_id


def get_subnet_ids_by_vpc_id(vpc_id):
    cmd = 'aws ec2 describe-subnets --filters "Name=vpc-id,Values=' + vpc_id + '" --query "Subnets[*].SubnetId" --output text'
    subnet_ids = ExecShellCommand(cmd, 'get subnet ids')
    return subnet_ids.split('\t')


def get_rds_endpoint(dbInstanceIdentifier):
    cmd = 'aws rds describe-db-instances --db-instance-identifier ' + dbInstanceIdentifier + ' --query "DBInstances[*].Endpoint.Address" --output text'
    rds_endpoint = ExecShellCommand(cmd, 'get rds endpoint')
    return rds_endpoint


def get_bucket_list():
    cmd = 'aws s3api list-buckets --query "Buckets[].Name" --output text'
    buckets = ExecShellCommand(cmd, 'get bucket list')
    return buckets.split('\t')


def delete_subnets():
    vpc_id = get_vpc_id()
    subnet_ids = get_subnet_ids_by_vpc_id(vpc_id)
    for id in subnet_ids:        
        # print 'id = ' + id
        cmd = 'aws ec2 delete-subnet --subnet-id ' + id
        ExecShellCommand(cmd, 'delete subnet') 


def associate_subnets(RouteTableId, subnet_names):
    for name in subnet_names:
        subnet_id = get_subnet_id_by_Name(name)
        cmd = 'aws ec2 associate-route-table --route-table-id ' + RouteTableId + ' --subnet-id ' + subnet_id
        ExecShellCommand(cmd, 'associate subnet ' + name)


def get_RouteTableId():
    vpc_id = get_vpc_id()
    cmd = 'aws ec2 describe-route-tables --filters "Name=vpc-id,Values=' + vpc_id + '" --query "RouteTables[*].RouteTableId" --output text'
    RouteTableId = ExecShellCommand(cmd, 'get RouteTableId')
    return RouteTableId


def create_bucket():
    BucketName = _deployment_['common']['BUCKET']
    buckets = get_bucket_list()
    if not BucketName in buckets:
        cmd = 'aws s3api create-bucket --bucket ' + BucketName  + ' --region ' +  _deployment_['s3']['Region']
        ExecShellCommand(cmd, 'create bucket ' + BucketName)


def save_common_secton():
    #f_section = open(_deployment_['s3']['Name'], "w+")
    f_section = open(_deployment_['common']['CommonFileName'], "w+") 
    f_section.write("#\n")
    f_section.write("# " + _deployment_['common']['CommonFileName'] + "\n")
    f_section.write("#\n")
    for item in _deployment_['common']:
        f_section.write(item + "=" +  _deployment_['common'][item] + "\n")
    f_section.close()    


def upload_to_bucket():
    BucketName = _deployment_['common']['BUCKET']
    cmd = 'aws s3 cp ' + _deployment_['s3']['Name'] + ' s3://' + BucketName
    ExecShellCommand(cmd, 'cp common to bucket ' + BucketName)


def grant_allusers_to_bucket():
    BucketName = _deployment_['common']['BUCKET']
    cmd = 'aws s3api put-object-acl --bucket ' + BucketName + ' --key ' + _deployment_['s3']['Name'] + ' --grant-read uri=http://acs.amazonaws.com/groups/global/AllUsers'
    ExecShellCommand(cmd, 'grant read to object ' + _deployment_['s3']['Name'])

#
#  
#
def write_startup_h():
    f_startup = open(_deployment_['control']['startup'], "w+")
    line = '#!/bin/bash -ex'
    f_startup.write(line + "\n")
    line = 'exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1'
    f_startup.write(line + "\n")
    line = 'date'
    f_startup.write(line + "\n")
    #line = 'sleep 600'
    #f_startup.write(line + "\n")
    #line = 'BUCKET=' + _deployment_['common']['BUCKET']
    #f_startup.write(line + "\n")
    #line = 'COMMON=' + _deployment_['s3']['Name']
    #f_startup.write(line + "\n")
    f_startup.close()
    #
    # merge it with startup_template
    #
    cmd = 'cat ' + _deployment_['common']['CommonFileName'] + ' >> ' + _deployment_['control']['startup']
    ExecShellCommand(cmd, 'append settings to startup.sh file')
    #
    cmd = 'cat ' + _deployment_['control']['startup_template'] + ' >> ' + _deployment_['control']['startup']
    ExecShellCommand(cmd, 'append startup_template to startup.sh file')
    #
    cmd = 'chmod +x ' + _deployment_['control']['startup']
    ExecShellCommand(cmd, 'make it executable')


#
#  detailed operation functions
#


#
# [ec2_vpc_route_table] 
#
def add_igw_to_route(RouteTableId):
    igw_id = get_igw_id()
    cmd = 'aws ec2 create-route --route-table-id ' + RouteTableId + ' --destination-cidr-block 0.0.0.0/0 --gateway-id ' + igw_id
    ExecShellCommand(cmd, 'add igw to route')


def name_routetable():
    RouteTableId = get_RouteTableId()
    tag_resource(RouteTableId, _deployment_['ec2_vpc_route_table']['Name'])
    return RouteTableId    

#
# [ec2_vpc_route_table]
#
def build_vpc_route_tables():
    RouteTableId = name_routetable()
    add_igw_to_route(RouteTableId)
    associate_subnets(RouteTableId, _deployment_['ec2_vpc_route_table']['associated_subnets'])    


def delete_vpc_route_tables():
    # may not need to do anything. After deleting the igw, the deletion to the vpc would delete all 
    # associated elements 
    pass


#
# [rds_subnet_group]
#
def build_rds_subnet_group():
    PrepareTemplate('rds', 'create-db-subnet-group')
    subnet_names = _deployment_['rds_subnet_group']['associated_subnets']
    #subnet_ids = []
    subnet_ids_string = ''
    for name in subnet_names:
        subnet_id = get_subnet_id_by_Name(name)    
        # print 'subnet_id = ' + subnet_id
        if subnet_ids_string == '':
            subnet_ids_string = '"' + subnet_id + '"'
        else:
            subnet_ids_string += ',' + '"' + subnet_id + '"' 
        # subnet_ids.append(subnet_id)
    jqexpression = '\'{"DBSubnetGroupName":"' + _deployment_['rds_subnet_group']['Name'] \
        + '","DBSubnetGroupDescription":"' + _deployment_['rds_subnet_group']['Name'] \
        + '","SubnetIds": [' + subnet_ids_string + ']}\''
        # \
        #+ ',"Tags": [{"Name":"' + _deployment_['rds_subnet_group']['Name'] \
        #               + '","Componment":"' + _deployment_['common']['Componment']  \
        #               + '","Version":"' + _deployment_['common']['Version']  \
        #               + '","VpcName":"' + _deployment_['common']['VpcName']  \
        #               + '"}]' \
        #+ '}\'' 
    #print 'jqexpression = ' + jqexpression 
    Run_subcommand('rds','create-db-subnet-group',jqexpression) 


def delete_rds_subnet_group():
    cmd = 'aws rds delete-db-subnet-group --db-subnet-group-name ' + _deployment_['rds_subnet_group']['Name']
    ExecShellCommand(cmd, 'delete db subnet ' + _deployment_['rds_subnet_group']['Name'])


#
# [rds_dbcluster]
#
def build_rds_dbcluster():
    vpc_id = get_vpc_id() 
    # assume there is only ONE security group for RDB in the VPC
    security_group_id = get_security_group_id(vpc_id)
    _deployment_['rds_dbcluster']['json_data']['VpcSecurityGroupIds'] = [ security_group_id ]
    #pprint.pprint( _deployment_['rds_dbcluster']['json_data'] )
    PrepareInput('rds', 'create-db-cluster', _deployment_['rds_dbcluster']['json_data'])
    Run_subcommand_inputfile('rds','create-db-cluster')
    Sleep(60)
    _deployment_['common']['rds_endpoint'] = get_cluster_endpoint(_deployment_['rds_dbcluster']['json_data']['DBClusterIdentifier'])
    save_common_secton()


def delete_rds_dbcluster():
    cmd = 'aws rds delete-db-cluster --skip-final-snapshot --db-cluster-identifier ' + _deployment_['rds_dbcluster']['json_data']['DBClusterIdentifier']
    ExecShellCommand(cmd, 'delete rds db cluster' + _deployment_['rds_dbcluster']['json_data']['DBClusterIdentifier'])
    Sleep(60)                  

        
#
# [rds_aurora]
#
def build_rds_aurora():
    _deployment_['rds_aurora']['json_data']['Tags'] = [ {"Key":"Name","Value":_deployment_['rds_aurora']['Name']},\
                                                        {"Key":"Componment","Value":_deployment_['common']['Componment']},\
                                                        {"Key":"Version","Value":_deployment_['common']['Version']},\
                                                        {"Key":"VpcName","Value":_deployment_['common']['VpcName']} ]
    #pprint.pprint(_deployment_['rds_aurora']['json_data'])
    PrepareInput('rds', 'create-db-instance', _deployment_['rds_aurora']['json_data'])
    Run_subcommand_inputfile('rds','create-db-instance')
    Sleep(600)


def delete_rds_aurora():
    cmd = 'aws rds delete-db-instance --skip-final-snapshot --db-instance-identifier ' + _deployment_['rds_aurora']['json_data']['DBInstanceIdentifier'] 
    ExecShellCommand(cmd, 'delete rds ' + _deployment_['rds_aurora']['json_data']['DBInstanceIdentifier'])
    Sleep(600)


#
# [rds_mysql]
#
def build_rds_mysql():
    PrepareInput('rds', 'create-db-instance', _deployment_['rds_mysql']['json_data'])
    Run_subcommand_inputfile('rds','create-db-instance')
    Sleep(600)
    _deployment_['common']['rds_endpoint'] = get_rds_endpoint(_deployment_['rds_mysql']['json_data']['DBInstanceIdentifier'])
    save_common_secton()


def delete_rds_mysql():
    cmd = 'aws rds delete-db-instance --skip-final-snapshot --db-instance-identifier ' + _deployment_['rds_mysql']['json_data']['DBInstanceIdentifier']
    ExecShellCommand(cmd, 'delete rds ' + _deployment_['rds_mysql']['json_data']['DBInstanceIdentifier'])
    Sleep(600)


#
# [s3]
#
def build_s3():
    if _deployment_['s3']['CreateBucket'] == 'y': 
        create_bucket()
    #save_common_secton()
    #upload_to_bucket()
    #grant_allusers_to_bucket()
    write_startup_h()
    #Sleep(300)


def delete_s3():
    return
    #cmd = 'aws s3 rm s3://' + _deployment_['common']['BUCKET'] + '/ --recursive'
    #ExecShellCommand(cmd, 'delete contents in bucket  ' + _deployment_['common']['BUCKET'])
    #if _deployment_['s3']['CreateBucket'] == 'y':
    #    cmd = 'aws s3api delete-bucket --bucket ' + _deployment_['common']['BUCKET'] 
    #    #ExecShellCommand(cmd, 'delete bucket  ' + _deployment_['common']['BUCKET'])


#
# [ec2_elb]
#
def build_elb():
    _deployment_['ec2_elb']['json_data']['Subnets'] = [] 
    for subnet in _deployment_['ec2_elb']['subnets']:
        _deployment_['ec2_elb']['json_data']['Subnets'].append(get_subnet_id_by_Name(subnet)) 
    # create-load-balancer
    _deployment_['ec2_elb']['json_data']['Tags'] = _deployment_['common']['Tags']
    _deployment_['ec2_elb']['json_data']['Tags'].append({"Key": "Name", "Value": _deployment_['ec2_elb']['Name']})
    PrepareInput('elb', 'create-load-balancer', _deployment_['ec2_elb']['json_data'])
    Run_subcommand_inputfile('elb','create-load-balancer')    
    # configure-health-check
    PrepareInput('elb', 'configure-health-check', _deployment_['ec2_elb']['configure-health-check']['json_data'])
    Run_subcommand_inputfile('elb','configure-health-check') 
    


    
def delete_elb():
    cmd = 'aws elb delete-load-balancer --load-balancer-name ' + _deployment_['ec2_elb']['Name']
    ExecShellCommand(cmd, 'delete elb ' + _deployment_['ec2_elb']['Name'])

    
#
# [ec2_lc]
#
def build_lc():
    #
    write_startup_h()
    #
    cmd = 'aws autoscaling create-launch-configuration' \
          + ' --launch-configuration-name ' + _deployment_['ec2_lc']['Name'] \
          + ' --key-name ' + _deployment_['ec2_lc']['KeyName'] \
          + ' --image-id ' + _deployment_['ec2_lc']['ImageId'] \
          + ' --instance-type ' + _deployment_['ec2_lc']['InstanceType'] \
          + ' --user-data file://' + _deployment_['control']['startup']
    ExecShellCommand(cmd, 'create launch configuration  ' + _deployment_['ec2_lc']['Name'])      
     

def delete_lc():
    cmd = 'aws autoscaling delete-launch-configuration --launch-configuration-name ' + _deployment_['ec2_lc']['Name']
    ExecShellCommand(cmd, 'delete launch configuration ' + _deployment_['ec2_lc']['Name'])


#
# [ec2_asg]
#
def build_asg():
    # Step 1: Create an Auto Scaling Group 
    subnet_list = ''
    for subnet in _deployment_['ec2_asg']['subnets']:
        subnet_list += get_subnet_id_by_Name(subnet) + ','
    cmd = 'aws autoscaling create-auto-scaling-group' \
        + ' --auto-scaling-group-name ' + _deployment_['ec2_asg']['Name'] \
        + ' --launch-configuration-name ' +  _deployment_['ec2_lc']['Name'] \
        + ' --load-balancer-names ' +  _deployment_['ec2_elb']['Name'] \
        + ' --min-size ' + _deployment_['ec2_asg']['min-size'] \
        + ' --max-size ' + _deployment_['ec2_asg']['max-size'] \
        + ' --vpc-zone-identifier ' + subnet_list \
        + ' --tags Key="Name",Value="' + _deployment_['ec2_asg']['Name'] + '"' \
        + ' Key="Componment",Value="' + _deployment_['common']['Componment'] + '"' \
        + ' Key="Version",Value="' + _deployment_['common']['Version'] + '"' \
        + ' Key="VpcName",Value="' + _deployment_['common']['VpcName'] + '"'
    ExecShellCommand(cmd, 'create autoscaling group ' + _deployment_['ec2_asg']['Name'])
    Sleep(60)
    #
    # add policies & alarms
    #
    for policy, alarm in zip(_deployment_['ec2_asg']['policies'], _deployment_['ec2_asg']['alarms']):
        # Step 2: Create Scaling Policies
        cmd = 'aws autoscaling put-scaling-policy --policy-name ' + policy['policy-name'] \
            + ' --auto-scaling-group-name ' + _deployment_['ec2_asg']['Name'] \
            + ' --scaling-adjustment ' + policy['scaling-adjustment'] \
            + ' --adjustment-type ' + policy['adjustment-type'] \
            + ' > ./templates/put-scaling-policy.output'
        #print cmd
        ExecShellCommand(cmd, 'create Scaling Policies') 
        # 
        # Step 3: Create CloudWatch Alarms
        PolicyARN = get_PolicyARN()
        #print 'PolicyARN = ' + PolicyARN
        cmd = 'aws cloudwatch put-metric-alarm --alarm-name ' + alarm['alarm-name'] \
            + ' --metric-name ' + alarm['metric-name'] \
            + ' --namespace AWS/EC2 --statistic Average ' \
            + ' --period ' + alarm['period'] \
            + ' --threshold ' + alarm['threshold'] \
            + ' --comparison-operator ' + alarm['comparison-operator'] \
            + ' --dimensions "Name=AutoScalingGroupName,Value=' + _deployment_['ec2_asg']['Name']  \
            + '" --evaluation-periods ' + alarm['evaluation-periods'] \
            + ' --alarm-actions ' + PolicyARN
        #print cmd
        ExecShellCommand(cmd, 'create CloudWatch Alarms')
        Sleep(60)    
    return


def delete_asg(): 
    cmd = 'aws autoscaling delete-auto-scaling-group' \
        + ' --auto-scaling-group-name ' + _deployment_['ec2_asg']['Name'] \
        + ' --force-delete'
    #print cmd
    ExecShellCommand(cmd, 'delete autoscaling group ' + _deployment_['ec2_asg']['Name']) 


#
# operation triage functions
#
def Build():
    for i in range(len(_deployment_['control']['modules'])):
        if _deployment_['control']['verbose'] == 'y':
            module = _deployment_['control']['modules'][i]
            WriteLine("# %s : %s" % (module, _deployment_[module]['Description']))
        if _deployment_['control']['modules'][i] == 'ec2_vpc':
            build_vpc()
        elif _deployment_['control']['modules'][i] == 'ec2_vpc_igw':
            build_igw()
        elif _deployment_['control']['modules'][i] == 'ec2_vpc_subnet':
            build_subnets()
        elif _deployment_['control']['modules'][i] == 'ec2_vpc_route_table':
            build_vpc_route_tables()
        elif _deployment_['control']['modules'][i] == 'rds_subnet_group':
            build_rds_subnet_group()
        elif _deployment_['control']['modules'][i] == 'rds_dbcluster':
            build_rds_dbcluster()
        elif _deployment_['control']['modules'][i] == 'rds_aurora':
            build_rds_aurora()
        elif _deployment_['control']['modules'][i] == 's3':
            build_s3()
        elif _deployment_['control']['modules'][i] == 'ec2_elb':
            build_elb()
        elif _deployment_['control']['modules'][i] == 'ec2_lc':
            build_lc()
        elif _deployment_['control']['modules'][i] == 'ec2_asg':
            build_asg()
        else:
            pass


def Delete():
    for i in range(len(_deployment_['control']['modules']) - 1, -1, -1):
        if _deployment_['control']['verbose'] == 'y':
            module = _deployment_['control']['modules'][i]
            WriteLine("# %s : %s" % (module, _deployment_[module]['Description']))
        if _deployment_['control']['modules'][i] == 'ec2_vpc':
            delete_vpc()
        elif _deployment_['control']['modules'][i] == 'ec2_vpc_igw':
            delete_igw()
        elif _deployment_['control']['modules'][i] == 'ec2_vpc_subnet':
            delete_subnets()
        elif _deployment_['control']['modules'][i] == 'ec2_vpc_route_table':
            delete_vpc_route_tables() 
        elif _deployment_['control']['modules'][i] == 'rds_subnet_group':
            delete_rds_subnet_group()
        elif _deployment_['control']['modules'][i] == 'rds_dbcluster':
            delete_rds_dbcluster()
        elif _deployment_['control']['modules'][i] == 'rds_aurora':
            delete_rds_aurora()
        elif _deployment_['control']['modules'][i] == 's3':
            delete_s3()
        elif _deployment_['control']['modules'][i] == 'ec2_elb':
            delete_elb()
        elif _deployment_['control']['modules'][i] == 'ec2_lc':
            delete_lc()
        elif _deployment_['control']['modules'][i] == 'ec2_asg':
            delete_asg()
        else:
            pass


#
# global functions
#
def ExecShellCommand(cmd, comment = ''):
    if comment != '':
        WriteLine('# ' + comment)
    WriteLine(cmd)
    if _deployment_['control']['dryrun'] == 'n':
        output = (0, ' ')
        output = commands.getstatusoutput(cmd)
        outputLines = output[1]
        for line in outputLines.split('\n'):
            WriteLine('# ' + line)
        if output[0] != 0:
            WriteLine('# Error: execution of ' + cmd + ' failed.')
            os._exit(1)
        return output[1]
    else:
        return ''


def Sleep(seconds):
    WriteLine('# Sleep for ' + str(seconds) + ' seconds')
    if _deployment_['control']['dryrun'] == 'n':
        time.sleep(seconds)


def WriteLine(line):
    try:
        print line
        if _f_ != None:
            _f_.write(line + "\n")
            _f_.flush()
    except IOError:
        pass


def GetCurrentTime():
    ts = datetime.datetime.now().__str__()
    ts = ts.replace("-","")
    ts = ts.replace(":","")
    ts = ts.replace(" ","_")
    ts = ts.replace(".","_")
    return (ts)


def CreateRptFile(filename):
    global _f_
    global _deployment_

    _deployment_['control']['timestamp'] = GetCurrentTime()
    _deployment_['control']['filename'] = filename.replace('.yaml', '')

    if _deployment_['control'].has_key('reportpath'):
        reportpath = _deployment_['control']['reportpath']
    else:
        reportpath = '.'
    reportfilename = reportpath + '/' + _deployment_['control']['filename']
    jsonfilename = reportfilename
    if _deployment_['control']['overwriteoldreport'] == 'y':
        reportfilename += '.rpt'
        jsonfilename += '.json'
    else:
        reportfilename += '_' + _deployment_['control']['timestamp']  + '.rpt'
        jsonfilename += '_' + _deployment_['control']['timestamp']  + '.json'

    _f_ = open(reportfilename, "w+")
    # output setting to .json file 
    f_json = open(jsonfilename, "w+")
    json.dump(_deployment_, f_json)    
    f_json.close()


def ReadCfgFile(filename):
    global _deployment_ 
    WriteLine('# Running Configuration File: ' + filename)

    # read .ini into _deployment_
    f_yaml = open(filename)
    _deployment_ = yaml.safe_load(f_yaml) 
    
    # record the running environment
    _deployment_['control']['filename'] = filename
    _deployment_['control']['version'] = _version_

    # create templates subdir 
    if not os.path.exists(os.path.join(os.getcwd(), 'templates')):
        os.mkdir('templates') 
    # create appsettings subdir
    if not os.path.exists(os.path.join(os.getcwd(), 'appsettings')):
        os.mkdir('appsettings')

    # create tags
    _deployment_['common']['Tags'] = [{"Key": "Componment", "Value": _deployment_['common']['Componment']},\
                                      {"Key": "Version", "Value": _deployment_['common']['Version']},\
                                      {"Key": "VpcName", "Value": _deployment_['common']['VpcName']}]

    # create .rpt file   
    CreateRptFile(filename)

    # debug
    if _deployment_['control']['debug'] == 'y':
        pprint.pprint(_deployment_)


def Version():
    WriteLine("\n awsclideploy " + _version_ + "\n")


def Usage():
    Version()
    WriteLine("Usage:\n$ ./awsclideploy.py { build | delete } { deployment.ini }\n")


def main():
    if len(sys.argv) == 3:
        start = time.time()
        operation = sys.argv[1]
        filename = sys.argv[2] 
        if (operation == 'build' or operation == 'delete') and os.path.exists(filename):
            ReadCfgFile(filename)
            WriteLine('# awsclideploy version %s' % _version_)
            if operation == 'build':
               Build()
            elif operation == 'delete':
               Delete()
            else:
               Usage()
        else:
            WriteLine('YAML file ' + sys.argv[2] + ' not exists.')
            os._exit(1)
        duration = (time.time() - start) / 60
        WriteLine('# Elapsed %.2f minutes.' % duration)
    else:
        Usage()
#
#
# starts here.
#
_version_ = "20.10"
_f_ = None
#
_deployment_ = {}
#
if __name__ == '__main__':
    main()


