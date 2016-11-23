#!/usr/bin/env python
#
# Niksun Enhanced QA Accuracy Test toolkit (mode 5 and mode 6)
# ------------------------------------------------------------
#
# eqat.py
#
# Yanming Xiao
# yxiao@niksun.com
#
# Run mode:
#   eqat.py {testsuite.ini}
#
# Debug mode: 
#   python -m pdb eqat.py {testsuite.ini}
#
#
# Tip:
#  tail -f /var/log/httpd-ssl_request.log | grep mainAnalysis_appliance
#
#  tail -f /var/log/httpd-ssl_request.log | grep UMTSAnalysis
#----------------------------------------------------------------------- 
# Measuring programming progress by lines of code is like measuring 
# aircraft building progress by weight. 
#
# --Bill Gates 
#----------------------------------------------------------------------- 
#
import sys
import os
import re
import pprint
import ConfigParser
import xml.dom.minidom
import xpath
import datetime
import commands
import operator
import sqlite3
import time

# math.trunc is new in version 2.6
import math

from lxml.etree import *
from copy import *
from decimal import Decimal

class TestCase(object):
    _tc = {}
    _demuxList = {}
    _demuxTupleSorted = ()
    _tupleFields = ()
    
    def __init__(self, section, resultfield):    
        self._tc = {}        
        self._tc['section'] = section
        #self._tc[resultfield] = 0
        self._demuxList = {}        
        
    def SortList(self):
        self._demuxTupleSorted = sorted(self._demuxList.iteritems(), \
            key = operator.itemgetter(1))
               
    def Output(self):
        print('--- _tc ---')
        pprint.pprint(self._tc)
        if len(self._demuxList) > 0:
            print('--- _demuxList ---')
            pprint.pprint(self._demuxList)
        if len(self._tupleFields) > 0:
            print('--- _tupleFields ---')
            pprint.pprint(self._tupleFields)


class BaseSection(object):
    _section = {}
    _expectedResultFile = ''
    _TestCaseList = []
    
    def __init__(self, type):
        self._section = {}    
    
    def Output(self):
        pprint.pprint(self._section)
        print '--- self._TestCaseList ---'
        for tc in self._TestCaseList:     
            tc.Output()


class ExpectedSection(BaseSection):
    _TestCaseList = []
    _Layer1Fields = {}
    _Layer2Fields = {}
    _Layer3Fields = {}

    def __init__(self, type):
        self._section = {}    
        self._section['type'] = type
        self._section['starttime'] = 'NoValue'
        self._section['endtime'] = '0'
        self._section['expectedresultfile'] = _qat_['expected'] + '.xml'
        self._section['expectedcsv'] = _qat_['expected'] + '.csv'
        self._section['layer1csv'] = 'layer1_' + _qat_['expected'] + '.csv'
        self._section['layer2csv'] = 'layer2_' + _qat_['expected'] + '.csv'
        self._section['layer3csv'] = 'layer3_' + _qat_['expected'] + '.csv'
        self._section['expectedtxt'] = _qat_['expected'] + '.txt'
        self._section['expecteddb'] = _qat_['expected'] + '.db'
        self._section['timestampfile'] = 'timestamp_' + _qat_['expected'] + '.xml'
        #self._section['starttimestamp'] = 'starttime_' + _qat_['expected'] + '.txt'
        #self._section['endtimestamp'] = 'endtime_' + _qat_['expected'] + '.txt'

    def Output(self):
        print('--- _expectedSection_ ---')
        super(ExpectedSection, self).Output()
        for testcase in self._TestCaseList:
            testcase.Output()
        if self._section.has_key('layer1'):
            print('--- _Layer1Fields ---')
            pprint.pprint(self._Layer1Fields)
        if self._section.has_key('layer2'):
            print('--- _Layer2Fields ---')
            pprint.pprint(self._Layer2Fields)
        if self._section.has_key('layer3'):
            print('--- _Layer3Fields ---')
            pprint.pprint(self._Layer3Fields)

    def RunCommand(self):
        cmd = ReplaceVariables(self._section['command'], self._section)
        ExecShellCommand(cmd)
                
    def GenerateTimeStamps(self):
        cmd = ReplaceVariables(self._section['generatetimestamps'], _qat_)
        ExecShellCommand(cmd)
      
    def GetLayerFieldValue(self, LayerNode, fieldxpathexpression):
        fieldValue = ''
        flagWriteThisField = False
        for field in LayerNode.xpath(fieldxpathexpression):
            fieldValue = field.get('show')
            flagWriteThisField = True
        return (fieldValue, flagWriteThisField)

            
    def ProcessPacketLayer3(self, L2, layer3KeyValue, f3):
        separator = '|'
        nFields = len(self._Layer3Fields)
        for layer3 in L2.xpath(self._section['layer3xpathstring']):
            L3 = Element("L3")
            L3.append(deepcopy(layer3))  
            if _qat_['debug'] == '2':
                WriteLine(tostring(L3))
            flagWrite = False
            line = ''
            for i in range(0, nFields):
                if i == 0:
                    fieldValue = layer3KeyValue
                else:
                    fieldValue, flagWriteThisField = self.GetLayerFieldValue(L3, 
                            self._Layer3Fields[str(i)])
                    flagWrite = flagWrite or flagWriteThisField                
                if i <  nFields - 1:  
                    line += fieldValue + separator 
                else:    
                    line += fieldValue
            if flagWrite:
                f3.write(line + "\n")                
                if _qat_['debug'] == '2':
                    WriteLine('layer3=' + line)
            L3.clear()
        return

        
    def ProcessPacketLayer2(self, L1, layer2KeyValue, f2, f3):
        separator = '|'
        CountLayer3Fields = len(self._Layer3Fields)                
        if CountLayer3Fields > 0:                
            keyLayer3 = int(self._Layer3Fields[str(0)])
        else:
            keyLayer3 = 0
        nFields = len(self._Layer2Fields)
        for layer2 in L1.xpath(self._section['layer2xpathstring']):
            L2 = Element('L2')
            L2.append(deepcopy(layer2))
            if _qat_['debug'] == '2':
                WriteLine(tostring(L2))
            line = ''
            flagWrite = False
            for i in range(0, nFields):
                if i == 0:
                    fieldValue = layer2KeyValue
                    layer3KeyValue = layer2KeyValue
                else:
                    fieldValue, flagWriteThisField = self.GetLayerFieldValue(L2, 
                            self._Layer2Fields[str(i)])
                    flagWrite = flagWrite or flagWriteThisField                
                    if i == keyLayer3:   
                        layer3KeyValue = fieldValue
                if i <  nFields - 1:  
                    line += fieldValue + separator 
                else:    
                    line += fieldValue
            if flagWrite:
                f2.write(line + "\n")                
                if _qat_['debug'] == '2':
                    WriteLine('layer2=' + line)
                if CountLayer3Fields > 0:
                    self.ProcessPacketLayer3(L2, layer3KeyValue, f3)
            L2.clear()
        return

    
    def ProcessPacketLayer1(self, L1, f1, f2, f3):
        if _qat_['debug'] == '2':
            WriteLine(tostring(L1))
        self.GetTimeStamps(L1)
        CountLayer2Fields = len(self._Layer2Fields)                
        if CountLayer2Fields > 0:                
            keyLayer2 = int(self._Layer2Fields[str(0)])
        else:   
            keyLayer2 = 0
        separator = '|'
        nFields = len(self._Layer1Fields)
        line = ''
        flagWrite = False
        for i in range(0, nFields):
            fieldValue, flagWriteThisField = self.GetLayerFieldValue(L1, 
                    self._Layer1Fields[str(i)])
            flagWrite = flagWrite or flagWriteThisField        
            if i == keyLayer2:   
                layer2KeyValue = fieldValue
            if i <  nFields - 1:  
                line += fieldValue + separator 
            else:    
                line += fieldValue
        if flagWrite:
            f1.write(line + "\n")                
            if _qat_['debug'] == '2':
                WriteLine('layer1=' + line)
            if CountLayer2Fields > 0:                
                self.ProcessPacketLayer2(L1, layer2KeyValue, f2, f3)
        return   
        
    def GenExpectedTxtFile(self):   
        f1 = None
        f2 = None
        f3 = None
        try:
            f1 = open(self._section['layer1csv'], "w+")
            if self._section.has_key('layer2csv'):
                f2 = open(self._section['layer2csv'], "w+")
            if self._section.has_key('layer3csv'):
                f3 = open(self._section['layer3csv'], "w+")
        except IOError:        
            print 'Expected result .csv file ' + self._section['layer1csv'] + ' can not be created.'                
            print 'Expected result .csv file ' + self._section['layer2csv'] + ' can not be created.'                
            print 'Expected result .csv file ' + self._section['layer3csv'] + ' can not be created.'                
            os._exit(1)    
            
        context = iterparse(self._section['expectedresultfile'], 
            events=('end',), tag='packet')
        for event, packet in context:
            L1 = Element('L1')
            # http://docs.python.org/2/library/copy.html
            L1.append(deepcopy(packet))
            #
            self.ProcessPacketLayer1(L1, f1, f2, f3)
            L1.clear()
            
        if f3 != None:
            f3.close()  
        if f2 != None:
            f2.close()  
        f1.close()  
            

    def WriteTimeStampFile(self):
        doc = Element('timestamp', 
            starttime=self._section['starttime'],
            endtime=self._section['endtime'])
        f = open(self._section['timestampfile'], 'w')
        f.write(tostring(doc))
        f.close()

        
    def GetTimeStampsFromTimeStampFile(self):   
        timestamptree = None
        try:
            timestamptree = parse(self._section['timestampfile'], parser = XMLParser())
        except IOError:        
            print 'Expected time stamp file ' + self._section['timestampfile'] + ' not exists.'                
            os._exit(1)    

        nodes = timestamptree.xpath('/timestamp')
        self._section['starttime'] = nodes[0].get('starttime')
        self._section['endtime'] = nodes[0].get('endtime')

   
    def CreateDb(self):
        cmd = ReplaceVariables(self._section['createdb'], _qat_)
        ExecShellCommand(cmd)
    
    def GenerateExpectedResult(self):
        if self._section['generateexpected'] == '1':
            if _qat_['debug'] != '2':
                self.RunCommand()
            if _qat_['mode'] == '5':
                self.GenExpectedTxtFile()
                self.WriteTimeStampFile()
            elif _qat_['mode'] == '6':
                if self._section.has_key('generatetimestamps'):
                    self.GenerateTimeStamps()
                    self.GetTimeStampsFromTimeStampFile()
                else:
                    self.WriteTimeStampFile()
            self.CreateDb()
        else:    
            self.GetTimeStampsFromTimeStampFile()

  
    def QueryExpectedResult(self):
        dbconnection = sqlite3.connect(self._section['expecteddb'])
        self.EnumTestCases(dbconnection)
        dbconnection.close()    

        
    def EnumTestCases(self, dbconnection):
        for testcase in self._TestCaseList:     
            if testcase._tc['operation'] == '14':
                self.Op14Func(dbconnection, testcase)
            elif testcase._tc['operation'] == '15':
                self.Op15Func(dbconnection, testcase)
            elif testcase._tc['operation'] == '16':
                self.Op16Func(dbconnection, testcase)
            elif testcase._tc['operation'] == '17':
                self.Op17Func(dbconnection, testcase)
            elif testcase._tc['operation'] == '18':
                self.Op18Func(dbconnection, testcase)
            else:
                WriteLine('expected operation ' + testcase._tc['operation'] + ' is not implemented in this version.')       
                os._exit(1)        

    def SortExpectedResult(self):
        for testcase in self._TestCaseList:     
            testcase.SortList()
   
    def GetTimeStamps(self, subtree):
        nodes = subtree.xpath(self._section['timestampxpathstring'])
        self._section['endtime'] = nodes[0].get(self._section['timestampfield'])    
        if self._section['starttime'] == 'NoValue':
            self._section['starttime'] = self._section['endtime']

    def Op14Func(self, dbconnection, testcase):
        fsql = None
        try:
            fsql = open(testcase._tc['queryscript'], 'r')
        except IOError:        
            print 'Query script file ' + testcase._tc['queryscript'] + ' not exists.'                
            os._exit(1)    
        sqlstatement = fsql.read()
        try:
            cursor = dbconnection.cursor()
            cursor.execute(sqlstatement)
            resultrecord = cursor.fetchone()
            while resultrecord is not None:
                testcase._demuxList[resultrecord[0]] = resultrecord[1]
                resultrecord = cursor.fetchone()
            cursor.close()
        except:
            print 'Query script file ' + testcase._tc['queryscript'] + ' has errors.'                
            os._exit(1)    


    def Op15Func(self, dbconnection, testcase):
        fsql = None
        try:
            fsql = open(testcase._tc['queryscript'], 'r')
        except IOError:        
            print 'Query script file ' + testcase._tc['queryscript'] + ' not exists.'                
            os._exit(1)    
        sqlstatement = fsql.read()
        try:
            cursor = dbconnection.cursor()
            cursor.execute(sqlstatement)
            resultrecord = cursor.fetchone()
            while resultrecord is not None:
                key = resultrecord[0] + testcase._tc['separator'] + resultrecord[1]
                testcase._demuxList[key] = resultrecord[2]
                resultrecord = cursor.fetchone()
            cursor.close()
        except:
            print 'Query script file ' + testcase._tc['queryscript'] + ' has errors.'                
            os._exit(1)    


    def Op16Func(self, dbconnection, testcase):
        fsql = None
        try:
            fsql = open(testcase._tc['queryscript'], 'r')
        except IOError:        
            print 'Query script file ' + testcase._tc['queryscript'] + ' not exists.'                
            os._exit(1)    
        sqlstatement = fsql.read()
        try:
            cursor = dbconnection.cursor()
            cursor.execute(sqlstatement)
            resultrecord = cursor.fetchone()
            while resultrecord is not None:
                if resultrecord[0] is not None:
                    testcase._demuxList[testcase._tc['name']] = resultrecord[0]
                else:    
                    testcase._demuxList[testcase._tc['name']] = 0
                resultrecord = cursor.fetchone()
            cursor.close()
        except:
            print 'Query script file ' + testcase._tc['queryscript'] + ' has errors.'                
            os._exit(1)    
        
    def Op17Func(self, dbconnection, testcase):
        fsql = None
        try:
            fsql = open(testcase._tc['queryscript'], 'r')
        except IOError:        
            print 'Query script file ' + testcase._tc['queryscript'] + ' not exists.'                
            os._exit(1)    
        sqlstatement = fsql.read()
        try:
            cursor = dbconnection.cursor()
            cursor.execute(sqlstatement)
            resultrecord = cursor.fetchone()
            while resultrecord is not None:
                strValue = str(resultrecord[1])
                if testcase._tc.has_key('pattern4value'):
                    pattern4value = testcase._tc['pattern4value']
                    if pattern4value != None:
                        strValue = getRegexVariable(strValue, pattern4value)
                testcase._demuxList[resultrecord[0]] = strValue        
                resultrecord = cursor.fetchone()
            cursor.close()
        except:
            print 'Query script file ' + testcase._tc['queryscript'] + ' has errors.'                
            os._exit(1)    

  
class ActualSection(BaseSection):
    _actualResultFile = ''
    _TestCaseList = []
    _displaykeys = {}
    
    def __init__(self, type):
        self._section['type'] = type
        self._section['actualresultfile'] = _qat_['actual'] + '.xml'
        self._section['aboutresultfile'] = 'about_' + _qat_['actual'] + '.xml'
        self._section['authresultfile'] = 'auth_' + _qat_['actual'] + '.xml'
        self._section['viewsfile'] = 'views_' + _qat_['actual'] + '.xml'
        self._TestCaseList = []
                
    def Output(self):
        print('--- _actualSection_ ---')
        super(ActualSection, self).Output()
        if self._section.has_key('displaykeys'):
            print('--- _actualSection_._displaykeys ---')
            pprint.pprint(self._displaykeys)

    def RmCookies(self):
        cmd = ReplaceVariables(self._section['rmcookies'], self._section)
        ExecShellCommand(cmd)

    def RmActualResultFile(self):
        cmd = ReplaceVariables(self._section['rmactualresultfile'], self._section)
        ExecShellCommand(cmd)

    def Login(self):
        cmd = ReplaceVariables(self._section['login'], self._section)
        ExecShellCommand(cmd)


    def CheckLoginStatus(self):
        dataSource = None
        try:
            dataSource = open(self._section['authresultfile'], 'r')
        except IOError:        
            print 'Actual auth file ' + self._section['authresultfile'] + ' not exists.'                
            os._exit(1)    
        try:
            xmlDoc = xml.dom.minidom.parse(dataSource)
        except :        
            print self._section['authresultfile'], 'is invalid.'                          
            os._exit(2)         
        try:
            '''
            lxml does NOT work with the xpath expression '/ns2:status'
            '''
            loginStatus = xmlDoc.getElementsByTagName("ns2:status")[0].firstChild.data
            if loginStatus != 'success':
                print 'Fail to login, errcode 2, stopped.'
                os._exit(2)         
        except :        
            print 'Fail to login, errcode 1, stopped.'
            os._exit(1)         

    def ListView(self):
        cmd = ReplaceVariables(self._section['listview'], self._section)
        ExecShellCommand(cmd)
        
    def About(self):
        cmd = ReplaceVariables(self._section['about'], self._section)
        ExecShellCommand(cmd)
    
    def Logout(self):
        cmd = ReplaceVariables(self._section['logout'], self._section)
        ExecShellCommand(cmd)

    def RestfulAPI(self, starttime, endtime):
        adjusted_endtime = Decimal(endtime) + Decimal('0.000001')
        self._section['endtime'] = str(adjusted_endtime)
        self._section['starttime'] = starttime

        baseURL = ReplaceVariables(self._section['baseurl'], self._section)
        self._section['baseurl'] = baseURL

        cmd = ReplaceVariables(self._section['restfulapi'], self._section)
        ExecShellCommand(cmd)

    def IsFeatureLicensed(self):
        if self._section['generateactual'] == '1':           
            self.RmCookies()
            self.Login()
            self.CheckLoginStatus()
            self.ListView()
            if self.CheckFeatureStatus():
                returnValue = True
            else:
                self.Logout()    
                self.RmCookies()
                WriteLine('('
                    + self._section['apptarget'] + ','  \
                    + self._section['view'] + ','           \
                    + self._section['pod'] + ') is not configured on '            \
                    + self._section['recorder'])
                returnValue = False
        else:
            returnValue = True
        return (returnValue)
    
    def GenerateActualResult(self, starttime, endtime):
        if self._section['generateactual'] == '1':           
            self.About()
            self.RestfulAPI(starttime, endtime)            
            self.Logout()
            self.RmCookies()
        self.QueryAbout()

    def QueryAbout(self):
        resulttree = None
        try:
            resulttree = parse(self._section['aboutresultfile'], parser = XMLParser())
        except :        
            print self._section['aboutresultfile'], 'is invalid.'                
            os._exit(2)   
        productInfoNodes = resulttree.xpath('/productInfo')
        for node in productInfoNodes:
            self._section['buildNumber'] = node.get('buildNumber')
            self._section['unitID'] = node.get('unitID')
            self._section['productName'] = node.get('productName')
        
    def CheckFeatureStatus(self):
        dataSource = None
        try:
            dataSource = open(self._section['viewsfile'], 'r')
        except IOError:        
            print 'Views file ' + self._section['viewsfile'] + ' not exists.'                
            os._exit(1)    
        try:
            xmlDoc = xml.dom.minidom.parse(dataSource)
        except :        
            print self._section['viewsfile'], 'is invalid.'                          
            os._exit(2)         

        if self._section['apptarget'] == 'analysis':
            returnValue = self.CheckAnalysisFeature(xmlDoc)
        elif self._section['apptarget'] == 'report':    
            returnValue = self.CheckReportFeature(xmlDoc)
        elif self._section['apptarget'] == 'appRecon':    
            returnValue = self.CheckAppReconFeature(xmlDoc)
        else:    
            returnValue = False
        return (returnValue)   

    def CheckAnalysisFeature(self, xmlDoc):            
        viewxpathstring = '/ns3:views/view[@category="' \
                        + self._section['apptarget']    \
                        + '" and @id="'                 \
                        + self._section['view']         \
                        + '"]'
        Pods = self._section['pod'].split(',')                
        ViewNodes = xpath.find(viewxpathstring, xmlDoc)
        returnValue = False
        for nodeView in ViewNodes:
            returnValue = True
            for pod in Pods:
                podxpathstring = '//pod[@id="' + pod + '"]' 
                PodNodes = xpath.find(podxpathstring, xmlDoc)
                if len(PodNodes) == 0:   
                    returnValue = False
        return(returnValue)
        
    def CheckReportFeature(self, xmlDoc):            
        '''
        /reportList/category/category/report[@id="36"]
        '''
        viewxpathstring = '/reportList/category/category/report[@id="' \
                        + self._section['view'] + '"]'
        ViewNodes = xpath.find(viewxpathstring, xmlDoc)
        if len(ViewNodes) == 0:   
            returnValue = False
        else:
            returnValue = True
        return(returnValue)

    def CheckAppReconFeature(self, xmlDoc):            
        '''
        <subMenu acl="tr" id="AppRecon" isAccessRight="false" licenseId="TCP_Recon" openable="on" url="AppRecon_m.swf?appTarget=appRecon" visible="true" />
        '''
        viewxpathstring = '/menu/subMenu[@id="AppRecon"]'
        ViewNodes = xpath.find(viewxpathstring, xmlDoc)
        if len(ViewNodes) == 0:   
            returnValue = False
        else:
            returnValue = True
        return(returnValue)

    def QueryActualResult(self):
        resulttree = None
        try:
            resulttree = parse(self._section['actualresultfile'], parser = XMLParser())
        except :        
            print self._section['actualresultfile'], 'is invalid.'                
            os._exit(2)   
        for testcase in self._TestCaseList:        
            if testcase._tc['operation'] == '0':
                self.Op0Func(resulttree, testcase)
            elif testcase._tc['operation'] == '1':
                self.Op1Func(resulttree, testcase)               
            elif testcase._tc['operation'] == '2':
                self.Op2Func(resulttree, testcase)               
            elif testcase._tc['operation'] == '3':
                self.Op3Func(resulttree, testcase)               
            elif testcase._tc['operation'] == '4':
                self.Op4Func(resulttree, testcase)               
            elif testcase._tc['operation'] == '5':
                self.Op5Func(resulttree, testcase)               
            elif testcase._tc['operation'] == '6':
                self.Op6Func(resulttree, testcase)               
            else:
                WriteLine('actual operation ' + testcase._tc['operation'] + ' is not implemented in this version.')
                os._exit(1)        

    def Op0Func(self, resulttree, testcase):     
        actualValue = 0
        DarDomNodes = resulttree.xpath(testcase._tc['dar_xpathstring'])
        for node in DarDomNodes:
            actualValue += int(float(node.get(testcase._tc['dar_field'])))
        PortDomNodes = resulttree.xpath(testcase._tc['port_xpathstring'])
        for node in PortDomNodes:
            actualValue += int(float(node.get(testcase._tc['port_field'])))
        testcase._demuxList[testcase._tc['name']] = actualValue

    def Op1Func(self, resulttree, testcase):     
        Nodes = resulttree.xpath(testcase._tc['demux_xpathstring'])
        for node in Nodes:
            demuxItem = str(node.get(testcase._tc['demux_field']))
            demuxItem = unicode(demuxItem, 'utf-8')
            if demuxItem != 'totals' and demuxItem != 'N/A':
                strValues = (str(node.get(testcase._tc['demux_value']))).split('.')
                # math.trunc is new in version 2.6
                if testcase._demuxList.has_key(demuxItem):
                    testcase._demuxList[demuxItem] += math.trunc(float(strValues[0]))
                else:    
                    testcase._demuxList[demuxItem] = math.trunc(float(strValues[0]))
                #testcase._demuxList[demuxItem] = int(strValues[0])

    def Op2Func(self, resulttree, testcase):     
        Nodes = resulttree.xpath(testcase._tc['list_xpathstring'])
        for node in Nodes:
            demuxItem = node.get(testcase._tc['list_field'])
            if testcase._tc.has_key('pattern4field'):
                pattern4field = testcase._tc['pattern4field']
                if pattern4field != None:
                    demuxItem = getRegexVariable(demuxItem, pattern4field)

            demuxItem = unicode(demuxItem, 'utf-8')
            strValue = node.get(testcase._tc['list_value'])
            if testcase._tc.has_key('pattern4value'):
                pattern4value = testcase._tc['pattern4value']
                if pattern4value != None:
                    strValue = getRegexVariable(strValue, pattern4value)
            testcase._demuxList[demuxItem] = strValue

                       
    def Op3Func(self, resulttree, testcase):     
        Nodes = resulttree.xpath(testcase._tc['demux_xpathstring'])
        demuxItem = testcase._tc['name']
        testcase._demuxList[demuxItem] = len(Nodes)

    def Op4Func(self, resulttree, testcase):     
        Nodes = resulttree.xpath(testcase._tc['demux_xpathstring'])
        for node in Nodes:
            demuxItem1 = str(node.get(testcase._tc['demux_field1']))
            demuxItem2 = str(node.get(testcase._tc['demux_field2']))
            separator = testcase._tc['separator']
            demuxItem = demuxItem1 + separator + demuxItem2
            demuxItem = unicode(demuxItem, 'utf-8')
            if demuxItem != 'totals' and demuxItem != 'N/A':
                strValues = (str(node.get(testcase._tc['demux_value']))).split('.')
                if testcase._demuxList.has_key(demuxItem):
                    testcase._demuxList[demuxItem] += math.trunc(float(strValues[0]))
                else:    
                    testcase._demuxList[demuxItem] = math.trunc(float(strValues[0]))

    def Op5Func(self, resulttree, testcase):     
        Nodes = resulttree.xpath(testcase._tc['demux_xpathstring'])
        for node in Nodes:
            demuxItem1 = str(node.get(testcase._tc['demux_field1']))
            demuxItem2 = str(node.get(testcase._tc['demux_field2']))
            separator = testcase._tc['separator']
            demuxItem = demuxItem1 + separator + demuxItem2
            demuxItem = unicode(demuxItem, 'utf-8')
            if demuxItem != 'totals' and demuxItem != 'N/A':
                strValues = node.get(testcase._tc['demux_value'])
                if testcase._demuxList.has_key(demuxItem):
                    testcase._demuxList[demuxItem] += float(strValues)
                else:    
                    testcase._demuxList[demuxItem] = float(strValues)

    def Op6Func(self, resulttree, testcase):     
        Nodes = resulttree.xpath(testcase._tc['list_xpathstring'])
        for node in Nodes:
            demuxItem1 = node.get(testcase._tc['list_field1'])
            separator = testcase._tc['separator']
            if separator != None:
                demuxItem2 = testcase._tc['list_field2']
                demuxItem = demuxItem1 + separator + demuxItem2

            demuxItem = unicode(demuxItem, 'utf-8')
            strValue = node.get(testcase._tc['list_value'])
            if testcase._tc.has_key('pattern4value'):
                pattern4value = testcase._tc['pattern4value']
                if pattern4value != None:
                    strValue = getRegexVariable(strValue, pattern4value)
            testcase._demuxList[demuxItem] = strValue[0]



def ReadConfigSecion(config, section, sectionDictionary):   
    try:
        options = config.options(section)
    except ConfigParser.NoSectionError:
        print "\n\nError:"
        print 'Section [' + section +  '] not exists.'                
        os._exit(1)    
    for option in options:
        sectionDictionary[option] = config.get(section, option)


def ReadConfigSecion2(displaykeysfile, sectionDictionary):   
    f = None
    try:
        f = open(displaykeysfile)
    except ConfigParser.NoSectionError:
        print "\n\nError:"
        print 'displaykeysfile ' + displaykeysfile + ' not exists.'                
        os._exit(1)    
    for line in f:
        if (line[0] != '#') and (line[0] != '[') and (line != '\n'):
            line = line.replace('\n','')
            valuePair = line.split('=')            
            sectionDictionary[valuePair[0]] = valuePair[1]
    f.close()       

def ReadConfigFile(config, sectionDictionary):   
    global _expectedSection_, _actualSection_
    ReadConfigSecion(config, 'qat', sectionDictionary)   
    # expected 
    _expectedSection_ = ExpectedSection('expected')
    section = sectionDictionary['expected']
    ReadConfigSecion(config, section, _expectedSection_._section)    
    if _expectedSection_._section.has_key('layer1'):
        ReadConfigSecion(config, _expectedSection_._section['layer1'], \
            _expectedSection_._Layer1Fields)
    if _expectedSection_._section.has_key('layer2'):
        ReadConfigSecion(config, _expectedSection_._section['layer2'], \
            _expectedSection_._Layer2Fields)
    if _expectedSection_._section.has_key('layer3'):
        ReadConfigSecion(config, _expectedSection_._section['layer3'], \
            _expectedSection_._Layer3Fields)
    expectedTCS = _expectedSection_._section['expectedtestcases'].split(',')
    for expectedtc in expectedTCS:
        expectedTestCase = TestCase(expectedtc, 'expectedvalue')
        ReadConfigSecion(config, expectedtc, expectedTestCase._tc)
        _expectedSection_._TestCaseList.append(expectedTestCase)
    # actual
    _actualSection_ = ActualSection('actual')
    section = sectionDictionary['actual']
    ReadConfigSecion(config, section, _actualSection_._section)
    if _actualSection_._section.has_key('displaykeys'):
        ReadConfigSecion(config, _actualSection_._section['displaykeys'], 
            _actualSection_._displaykeys)
    if _actualSection_._section.has_key('displaykeysfile'):        
        ReadConfigSecion2(_actualSection_._section['displaykeysfile'], \
            _actualSection_._displaykeys)
    actualTCS = _actualSection_._section['actualtestcases'].split(',')
    for actualtc in actualTCS:
        actualTestCase = TestCase(actualtc, 'actualvalue')
        ReadConfigSecion(config, actualtc, actualTestCase._tc)
        _actualSection_._TestCaseList.append(actualTestCase)
      
    #DebugOutput()
    if len(_actualSection_._TestCaseList) != len(_actualSection_._TestCaseList):
        WriteLine("len(_actualSection_._TestCaseList) != len(_actualSection_._TestCaseList), stopped.")
        os._exit(1)    
    
    
def repeat(s, n):
    return ''.join([s] * n)
    
    
def CompareResults(testsuiteConfigFile, expectedTCList, actualTCList, displaykeys):
    global _totalTCs_
    global _passedTCs_
        
    WriteLine('==================== Test Suite ===================')
    WriteLine('suite    : ' + testsuiteConfigFile)
    WriteLine('subject  : ' + _qat_['subject'])
    WriteLine('title    : ' + _qat_['title'])
    WriteLine('host     : ' + _actualSection_._section['host'])
    WriteLine('recorder : ' + _actualSection_._section['recorder'])
    WriteLine('dataset  : ' + _actualSection_._section['dataset'])
    if _actualSection_._section.has_key('apptarget'):
        WriteLine('apptarget: ' + _actualSection_._section['apptarget'])
    WriteLine('view     : ' + _actualSection_._section['view'])
    if _actualSection_._section.has_key('layer'):
        WriteLine('layer    : ' + _actualSection_._section['layer'])
    WriteLine('pod      : ' + _actualSection_._section['pod'])
    WriteLine('===================== Unit ========================')
    WriteLine('unitID       : ' + _actualSection_._section['unitID'])
    WriteLine('buildNumber  : ' + _actualSection_._section['buildNumber'])
    WriteLine('productName  : ' + _actualSection_._section['productName'])
    WriteLine('==================== Result =======================')
    _totalTCs_ = len(expectedTCList)
    passOrNot = 0
    for i in range(0, _totalTCs_):
        e = expectedTCList[i]
        a = actualTCList[i]
        WriteLine('name : ' + e._tc['name'])
        WriteLine('description : ' + e._tc['description'])            
        if a._tc.has_key('pod'):
            WriteLine('pod : ' + a._tc['pod'])            
        WriteLine('demux' + repeat('.', 23) + 'expected' \
            + repeat('.', 8) + 'actual' )
        lengthOfTuple = len(e._demuxTupleSorted)
        passOrNot = 1
        for j in range(0, lengthOfTuple):
            item = e._demuxTupleSorted[lengthOfTuple - 1 - j]
            key_expected = item[0]
            if displaykeys == None:
                key_actual = key_expected
            else:
                if key_expected in displaykeys:
                    key_actual = displaykeys[key_expected]
                    namecolumn = key_expected + '/' + key_actual
                else:
                    key_actual = key_expected
                    namecolumn = key_expected

            value_expected = e._demuxList[key_expected]

            if key_actual in a._demuxList:
                value_actual = a._demuxList[key_actual]
            else:   
                value_actual = 0
            countOfSpaces1 = 28 - len(str(namecolumn))
            if countOfSpaces1 <= 0:
                countOfSpaces1 = 1
            countOfSpaces2 = 16 - len(str(value_expected))
            if countOfSpaces2 <= 0:
                countOfSpaces2 = 1
            WriteLine(str(namecolumn) + repeat(' ', countOfSpaces1) \
                + str(value_expected) \
                + repeat(' ', countOfSpaces2) \
                + str(value_actual))

            if value_expected != value_actual:
                passOrNot = 0

        if passOrNot:
            WriteLine('--- Testcase ' + str(i) + ' passed ---\n')
            _passedTCs_ += 1
        else:    
            WriteLine('--- Testcase ' + str(i) + ' failed ---\n')           

def ReadTestSuiteFile(testsuiteConfigFile, sectionDictionary):
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    config.read(testsuiteConfigFile) 
    ReadConfigFile(config, sectionDictionary)


def ExecTestSuiteFile(testsuiteConfigFile):
    global _qat_
    
    WriteLine('Running Test Suite: ' + testsuiteConfigFile)
    # read .ini into _qat_
    _qat_['testsuiteConfigFile'] = testsuiteConfigFile
    ReadTestSuiteFile(testsuiteConfigFile, _qat_)
    
    if _qat_['mode'] != '5' and _qat_['mode'] != '6':
        WriteLine('mode ' + _qat_['mode'] + ' is not implemented in this version.')       
        os._exit(1)        
            
    # create result file
    CreateRptFile(testsuiteConfigFile)  
    
    # create result file
    if not _actualSection_.IsFeatureLicensed():
        WriteLine('\n')
        _f_.close()    
        os._exit(1)        
    
    # generate expected file in pdml or txt
    _expectedSection_.GenerateExpectedResult()
    # query expected results based on the value
    _expectedSection_.QueryExpectedResult() 
    # sort expected results based on the value
    _expectedSection_.SortExpectedResult()
              
    # generate actual result in xml
    _actualSection_.GenerateActualResult(_expectedSection_._section['starttime'], \
            _expectedSection_._section['endtime'])
       
    # query and get the actual results    
    _actualSection_.QueryActualResult()
    
    # compare expected results with that of actual
    CompareResults(testsuiteConfigFile,
        _expectedSection_._TestCaseList, \
        _actualSection_._TestCaseList, \
        _actualSection_._displaykeys)

    
def ExecShellCommand(cmd):    
    WriteLine("cmd:\t" + cmd)
    output = (0, ' ')
    output = commands.getstatusoutput(cmd)
    WriteLine(output[1])
    if output[0] != 0:
        WriteLine("Error: execution of " + cmd + " is failed.")
        os._exit(1)        
    
    
def ReplaceVariables(line, varDict):
    pattern = '\${(?P<variable>\w+)}'
    regex = re.compile(pattern)
    variables = regex.findall(line)
    for v in variables:
        if varDict.has_key(v):
            oldstring = '${' + v + '}'
            newstring = varDict[v]
            line = line.replace(oldstring, newstring)
        else:
            WriteLine('Variable ${' + v + '} is not defined.')
            os._exit(1)        
    return (line)


def getRegexVariable(original, pattern):
    regex = re.compile(pattern)
    r = regex.search(original)
    return (r.groupdict()['variable'])
    
    
def WriteLine(line):
    try:
        print line
        if _f_ != None:
            _f_.write(line + "\n")
    except IOError:
        pass


def DebugOutput():
    if _qat_['debug'] != '0':
        _expectedSection_.Output()
        _actualSection_.Output()
    
    
def CreateRptFile(testsuiteConfigFile):    
    global _f_
    global _startTime_

    if _qat_.has_key('reportpath'):
        reportpath = _qat_['reportpath']
    else:
        reportpath = '.'
    reportfile = reportpath + '/' + testsuiteConfigFile.replace('.ini', '')    
    if _qat_['overwriteoldreport'] == '1':
        reportfile += '.rpt'
    else:
        ts = datetime.datetime.now().__str__()
        ts = ts.replace("-","") 
        ts = ts.replace(":","") 
        ts = ts.replace(" ","_") 
        ts = ts.replace(".","_") 
        reportfile += '_' + ts + '.rpt'
        
    _f_ = open(reportfile, "w+")
    Version()    
    WriteLine("")    
    ts = datetime.datetime.now()
    _startTime_ = ts.__str__()

    
def Summary():
    global _f_        
    WriteLine('==================== Summary ======================')
    WriteLine("Start Time:\t" + _startTime_)    
    ts = datetime.datetime.now()
    WriteLine("End Time:\t" + ts.__str__())    
    pcntPassed = str(float((_passedTCs_ + 0.0) * 100 / _totalTCs_))[:5] + '%'
    pcntFailed = str(float((_totalTCs_ - _passedTCs_  + 0.0) * 100 / _totalTCs_))[:5] + '%'
    WriteLine(str(_passedTCs_) + ' of ' + str(_totalTCs_) \
        + ' (' + pcntPassed + ')\tpassed')
    WriteLine(str(_totalTCs_ - _passedTCs_) + ' of ' + str(_totalTCs_) \
        + ' (' + pcntFailed + ')\tfailed')
    if _f_ != None:
        WriteLine('\n')
        _f_.close()    
    
    if _qat_['debug'] != '0':
        print('--- globals ---')
        pprint.pprint(_qat_)
        DebugOutput()


def Version():    
    WriteLine("\n eqat (mode 5 and mode 6) " + version + " - Enhanced Qa Accuracy Test toolkit\n")


def Usage():
    Version()
    WriteLine("Usage:\n$ python eqat.py {testcases.ini}\n")


def main():
    if len(sys.argv) == 2:
        if os.path.exists(sys.argv[1]):
            ExecTestSuiteFile(sys.argv[1])
            Summary()
        else:
            WriteLine('INI file ' + sys.argv[1] + ' not exists.')
            os._exit(1)
    else:
        Usage()        

#
# starts here.
#
version="3.37"
#
_qat_ = {}
_Protocols_ = {}
_expectedSection_ = None
_actualSection_ = None
_f_ = None
_totalTCs_ = 0
_passedTCs_ = 0
_startTime_ = ''
if __name__ == '__main__':
    main()
os._exit(0)    
    
