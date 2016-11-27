#!/usr/bin/python
#
# Python Proxy
#
# https://code.google.com/p/python-proxy/
#
#
# <pproxy.py>
#
"""
Copyright (c) <2009> <Fabio Domingues - fnds3000 in gmail.com> <MIT Licence>

                  **************************************
                 *** Python Proxy - A Fast HTTP proxy ***
                  **************************************


Supportted HTTP methods:
 - OPTIONS;
 - GET;
 - HEAD;
 - POST;
 - PUT;
 - DELETE;
 - TRACE;
 - CONNECT.

"""
import sys
import socket, thread, select
#
import xml.etree.ElementTree
import logging
import pprint

__version__ = '0.2.2 (enhanced by Yanming Xiao)'
BUFLEN = 8192
VERSION = 'Python Proxy - A Fast HTTP proxy '+__version__
HTTPVER = 'HTTP/1.1'

class ConnectionHandler:
    def __init__(self, connection, address, timeout):
        self.client = connection
        self.client_buffer = ''
        self.timeout = timeout
        self.talker = ''
        self.method, self.path, self.protocol = self.get_base_header()
        #print "Client: %s %s" % (address, self.path)
        if self.method=='CONNECT':
            self.method_CONNECT()
        elif self.method in ('OPTIONS', 'GET', 'HEAD', 'POST', 'PUT',
                             'DELETE', 'TRACE'):
            self.method_others()

        self.client.close()
        self.target.close()

    def get_base_header(self):
        while 1:
            self.client_buffer += self.client.recv(BUFLEN)
            end = self.client_buffer.find('\n')
            if end!=-1:
                break
        #print('HEADER: %s' % self.client_buffer[:end]) #debug
        data = (self.client_buffer[:end+1]).split()
        self.client_buffer = self.client_buffer[end+1:]
        return data

    def method_CONNECT(self):
        try:
            self._connect_target(self.path)
            self.client.send(HTTPVER+' 200 Connection established\n'+
                             'Proxy-agent: %s\n\n'%VERSION)
        except:
            pass
        self.client_buffer = ''
        self._read_write()

    def method_others(self):
        self.path = self.path[7:]
        i = self.path.find('/')
        host = self.path[:i]
        path = self.path[i:]
        try:
            self._connect_target(host)
            self.target.send('%s %s %s\n'%(self.method, path, self.protocol)+
                             self.client_buffer)
        except:
            pass
        self.client_buffer = ''
        self._read_write()

    def _connect_target(self, host):
        i = host.find(':')
        if i!=-1:
            port = int(host[i+1:])
            host = host[:i]
        else:
            port = 80
        (soc_family, _, _, _, address) = socket.getaddrinfo(host, port)[0]
        self.target = socket.socket(soc_family)
        self.target.connect(address)

    def _read_write(self):
        time_out_max = self.timeout / 3
        socs = [self.client, self.target]
        count = 0
        while 1:
            count += 1
            (recv, _, error) = select.select(socs, [], socs, 3)
            if error:
                break
            if recv:
                for in_ in recv:
                    try:
                        data = in_.recv(BUFLEN)
                    except:
                        data = None
                    if in_ is self.client:
                        out = self.target
                        self.talker = 'CLIENT'
                    else:
                        out = self.client
                        self.talker = 'TARGET'
                    if data:
                        out.send(data)
                        self.monitorData(self.talker, data)
                        count = 0
            if count == time_out_max:
                break

    def monitorData(self, talker, content):
        strContent = None
        try:
            strContent = content.encode('utf-8')
        except:
            pass

        if strContent != None:
           listContent = strContent.split('\n')
           size = len(listContent)
           WriteLine('------ %s ------' % talker)
           i = 0
           for i in range(0, size):
                WriteLine( '%02d: %s' % (i, listContent[i]))
                i += 1


def WriteLine(line):
    logging.info(line)
    print(line)


def startServer(portStr='3128', IPv6=False, timeout=60,
                  handler=ConnectionHandler):
    if IPv6==True:
        soc_type = socket.AF_INET6
    else:
        soc_type = socket.AF_INET
    host = '0.0.0.0'
    port = int(portStr)
    soc = socket.socket(soc_type)
    soc.bind((host, port))
    print "Serving on %s:%d" % (host, port) #debug
    soc.listen(0)
    while 1:
        thread.start_new_thread(handler, soc.accept()+(timeout,))


def Usage():
    print VERSION
    print "Usage:\n$ ./pproxy.py [port]\n"

#
# starts from here
#
if __name__ == '__main__':
    logging.basicConfig(filename='pproxy.log', filemode='w', level=logging.INFO)
    #logging.captureWarnings(True)

    if len(sys.argv) == 2:
        print VERSION
        startServer(sys.argv[1])
    else:
        Usage()
        startServer()

