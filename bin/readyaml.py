#!/usr/bin/env python

import sys
import pprint

import yaml
import json




def func2():
    for policy, alarm in zip(_deployment_['ec2_asg']['policies'], _deployment_['ec2_asg']['alarms']):
        # Step 2: Create Scaling Policies
        cmd = 'aws autoscaling put-scaling-policy --policy-name ' + policy['policy-name'] \
              + ' --auto-scaling-group-name ' + _deployment_['ec2_asg']['Name'] \
              + ' --scaling-adjustment ' + policy['scaling-adjustment'] \
              + ' --adjustment-type ' + policy['adjustment-type'] \
              + ' > ./templates/put-scaling-policy.output'
        print cmd 
        #ExecShellCommand(cmd, 'create scaling policies') 
        #Sleep(60)
        #   
        # Step 3: Create CloudWatch Alarms
        PolicyARN = 'get_PolicyARN()'
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
        print cmd


def func1():
    for policy, alarm in zip(_deployment_['ec2_asg']['policies'], _deployment_['ec2_asg']['alarms']):
        pprint.pprint(policy)
        print '----------------------'
        pprint.pprint(alarm)
        print '======================'

#
#
#

f_yaml = open(sys.argv[1])
# use safe_load instead load
_deployment_ = yaml.safe_load(f_yaml)
pprint.pprint(_deployment_)

f_yaml.close()
#
#func1()
#func2()

#pprint.pprint(_deployment_['rds_aurora'])
 

f_json = open('templates/create-db-cluster.template')

_json_ = json.load(f_json, "utf-8")

f_json.close()

#json_data = open(file_directory).read()
#
#data = json.loads(json_data)
#pprint(data)

pprint.pprint(_json_)

_json_['AvailabilityZones'] = _deployment_['rds_aurora']['AvailabilityZones'] 


pprint.pprint(_json_)

outfile = open('./templates/create-db-cluster.input', 'w')
json.dump(_json_, outfile)
outfile.close

