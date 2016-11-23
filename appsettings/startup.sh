#!/bin/bash -ex
exec > >(tee /var/log/user-data.log | logger -t user-data -s 2>/dev/console) 2>&1
date
#
# ./appsettings/common-beta.sh
#
VpcName=vpcYX20
Version=BETA
TARGET=/opt/lampp/phpmyadmin/config.inc.php
rds_endpoint=rdsyx20.cluster-c8nf6ckx1dld.us-east-1.rds.amazonaws.com
CommonFileName=./appsettings/common-beta.sh
Componment=xampp
MyIP=47.19.17.202
#
# startup.template
# 
cd /root
cp "${TARGET}" old-1.txt
cat old-1.txt | sed -e "s/xxxxxxxx01/${rds_endpoint}/" > new-1.txt
cp new-1.txt "${TARGET}"
