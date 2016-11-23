# createBundle.sh
#
# http://doc.aws.amazon.com/elasticbeanstalk/latest/dg/using-features.deployment.source.html
#
PROJECT=$(basename $(pwd))
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
ZIPFILE=${PROJECT}_${TIMESTAMP}.zip
echo ${ZIPFILE}
#rm -f *.rpt *.json *~
zip ../Backups/${ZIPFILE} -r * .[^.]*
ls -l --color=auto ../Backups/*.zip
