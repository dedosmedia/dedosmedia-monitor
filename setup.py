#!/usr/bin/env python
# -*- coding: utf-8 -*-


#tar -zcvf image.tar.gz Dockerfile app

from __future__ import print_function
import os
import sys
import json
import time
import subprocess
from subprocess import *
import shutil
import posixpath
import logging
import logging.config
import gzip
from io import BytesIO
import signal
import imp

import monitor


'''
 TODO: Impleemntar colas, para permitir procesar más de un elemento.
        Guardar en carpetas con nombres automaticos cada proyecto para poder separar assets

        Que se monitoreen archivos con una expressin regular, asi se puedan poner muchos ficheros en mismo folder
        Que se pueda procesar con threads en simultanea
'''

### Global variables
config = json.loads('[]')
render_path = ''
config_path = ''
watch_path = ''
daemon = ''
aepx = ''
queue = []

    
### Constant: Config filename
APP_PATH = "/app"
CONFIG_PATH = "./config"
CONFIG_FILENAME = CONFIG_PATH+"/config.json"
CORE_FILENAME = CONFIG_PATH+"/core.dll"
WATCH_PATH = "./watch"
RENDER_PATH = "./render"
PORT = 4999
OUTPUT_NAME = "output{}.jpg"


### Creating dynamic library
if False:
    inF = file("masterCC.aepx", 'rb')
    s = inF.read()
    inF.close()
    outF = gzip.GzipFile("core.dll", 'wb')
    outF.write(s)
    outF.close()

### Setting up the container
def set_container():

    global render_path
    global config_path
    global watch_path
    
    log = logging.getLogger(__name__)

    ### Creating render structure for mounting on /app/render
    uri = ["AppData",
            "Roaming",
            "com.dedosmedia.SkinRetouching",
            "Local Store",
            "content",
            "Keshot",
            "compositions",
            "master",
            "input"
            ]
    render_path = os.path.join(os.path.expanduser("~"),*uri)
    if not os.path.exists(render_path):
        log.info("Creating rendering path on local disk.")
        try:
            os.makedirs(render_path)
        except OSError as error:
            log.error("ERROR: creating rendering structure on local disk. {}".format(error))
            exit(1)
    
    render_path = os.path.realpath(os.path.dirname(render_path))
    #print("Render path is: {} and exists: {}".format(render_path, os.path.exists(render_path)))

    ### Config path to mount on /app/config
    config_path = os.path.realpath(os.path.dirname(CONFIG_FILENAME))
    log.info("Config path is: {} and exists: {}".format(config_path, os.path.exists(config_path)))

    ### Watch path to mount on /app/watch
    watch_path = os.path.realpath(config["watch-folder-"+os.name])
    log.info("Watch path is: {} and exists: {}".format(watch_path, os.path.exists(watch_path)))

    try:
        folder = os.path.realpath(os.path.join(watch_path,config['output-subfolder']))
        os.makedirs(folder)
    except OSError as error:
        if os.path.exists(folder) == False:
            log.error("ERROR: creating watch output structure on local disk. {}".format(error))
            exit(1)
    log.info("Container started correctly. Monitoring: {}".format(os.path.realpath(os.path.join(watch_path,config["input-file"]))))
    

 

### Look for the daemon into the host
def get_daemon():
    log = logging.getLogger(__name__)
    try:
        global daemon
        global config
        log = logging.getLogger(__name__)
        if os.name == 'nt':
            daemon = 'C:/Program Files/Adobe/Adobe After Effects CC {0}/Support Files/aerender.exe'
        else:
            daemon = '/Applications/Adobe After Effects CC {0}/aerender'

        version = ["2014", "2014.1","2015", "2015.1", "2015.2", "2015.3"]

        for p in version:
            if os.path.exists(daemon.format(p)):
                break   
        
        if os.path.exists(daemon.format(p)) == False:
            log.error("ERROR: Missing required third-party software. Please contact support to install the required third-party software.")
            exit(1)

        daemon = daemon.format(p)
    except:
        log.error("Unable to get the daemon due to an unknown error.")
        exit(1)



### Start rendering process
def rendering(args):
    log = logging.getLogger(__name__)
     ### Logging configuration for Stdout
    try:
        devnull = None
        config["error"]
    except KeyError as error:
        devnull = open(os.devnull, 'w')

    try:
        log.info("Rendering...")
        start = time.time()
        subprocess.check_call(args,stdout=devnull, stderr=devnull)
        end = time.time()
        dt = end-start
        log.info("Time spent rendering: {}".format(dt))

        ### move the file to the real output
        try:
            ### TODO: Que pasa si hay mas de una imagen de salida??
            ###
            src = os.path.join(render_path,OUTPUT_NAME.format("0"))
            dst = os.path.normpath(os.path.join(watch_path,config["output-subfolder"],config['output-file']))
            shutil.move( src, dst)
        except OSError as error:
            log.warning("WARNING: moving file {}. Retrying.".format(error))
            os.remove(dst)
            shutil.move(src,dst)
            
        log.info("(((( DONE ))))))) - Monitoring again.")
       
        ## remove the aepx
        os.remove(args[2])
        
    except CalledProcessError as error:
        log.error("ERROR: rendering process failed with code {}".format(error))

    ### move the files to final location

def logging_config():
    global config
    # initialize logging
    try:
        logging_config = config["log-config"]

        # set up logging handlers filenames to absolute
        for handler in [ "file_all", "file_error" ]:
            log_file_name = logging_config["handlers"][handler]["filename"]
            log_file_path = os.path.abspath(os.path.join(".", log_file_name))
            logging_config["handlers"][handler]["filename"] = log_file_path
            #print("log path: {}".format(log_file_path))

        logging.config.dictConfig(logging_config)
        log = logging.getLogger(__name__)
        log.info("================================")
        log.info("Logging successfully initialized")
        log.info("================================")
    except:
        print("ERROR: Unable to initialize logging", file=sys.stderr)
        exit(1)


def main():
    global config

    ### Loads the configuration json
    try:
        config_path = os.path.realpath(CONFIG_FILENAME)
        with open(config_path) as data_file:
            config = json.load(data_file)
    except:
        print("ERROR: Unable to read config file {}. Please be sure the file exists and Docker has permission to read/wrtie it".format(CONFIG_FILENAME), file=sys.stderr)
        exit(1)

    logging_config()
    set_exit_handler(on_exit)
    get_daemon()
    set_container()


    
def set_exit_handler(func):
    if os.name == "nt":
        try:
            import win32api
            win32api.SetConsoleCtrlHandler(func, True)
        except ImportError:
            version = ".".join(map(str, sys.version_info[:2]))
            raise Exception("pywin32 not installed for Python " + version)
    else:
        import signal
        signal.signal(signal.SIGTERM, func)
        
def on_exit(sig, func=None):
    global container_id
    
    log = logging.getLogger(__name__)
    log.info("Cleaning up and exiting")
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)

    
### Entrypoint
if __name__ == "__main__":
    main();
    os.environ["CORE"] = CORE_FILENAME
    os.environ["CONFIG"] = CONFIG_FILENAME
    os.environ["WATCH"] = watch_path
    os.environ["RENDER"] = render_path
    os.environ["OUTPUT_NAME"] = OUTPUT_NAME
    os.environ["DAEMON"] = daemon
    monitor = monitor.Monitor()
    monitor.main()
    
