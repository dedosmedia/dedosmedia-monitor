#!/usr/bin/env python
# -*- coding: utf-8 -*-


#tar -zcvf image.tar.gz Dockerfile app

from __future__ import print_function
import os
import sys
import json
import logging
import logging.config
import gzip
import signal


# custom module
from monitor import Monitor


'''
 TODO: Impleemntar colas, para permitir procesar más de un elemento.
        Guardar en carpetas con nombres automaticos cada proyecto para poder separar assets

        Que se monitoreen archivos con una expressin regular, asi se puedan poner muchos ficheros en mismo folder
        Que se pueda procesar con threads en simultanea
'''
   
### Constant: Config filename
CONFIG_PATH = "./config"                                    # Folder name with all the config files needed
CONFIG_FILENAME = CONFIG_PATH+"/config.json"                # Config json filename
CORE_FILENAME = CONFIG_PATH+"/core.dll"                     # Config dll filename
OUTPUT_NAME = "output{}.jpg"                                # Output name for the rendering process. '{}' in 'output{}.jpg' are required



### Creating dynamic library
if False:
    inF = file("masterCC.aepx", 'rb')
    s = inF.read()
    inF.close()
    outF = gzip.GzipFile("core.dll", 'wb')
    outF.write(s)
    outF.close()

class Setup():

    ### Setting up the container
    def set_container(self):
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
        
        self.render_path = os.path.realpath(os.path.dirname(render_path))
        #print("Render path is: {} and exists: {}".format(render_path, os.path.exists(render_path)))

        ### Config path to mount on /app/config
        self.config_path = os.path.realpath(os.path.dirname(CONFIG_FILENAME))
        log.info("Config path is: {} and exists: {}".format(self.config_path, os.path.exists(self.config_path)))

        ### Watch path to mount on /app/watch
        self.watch_path = os.path.realpath(self.config["watch-folder-"+os.name])
        log.info("Watch path is: {} and exists: {}".format(self.watch_path, os.path.exists(self.watch_path)))

        try:
            folder = os.path.realpath(os.path.join(self.watch_path,self.config['output-subfolder']))
            os.makedirs(folder)
        except OSError as error:
            if os.path.exists(folder) == False:
                log.error("ERROR: creating watch output structure on local disk. {}".format(error))
                exit(1)
                
        log.info("Container started correctly. Monitoring: {}".format(os.path.realpath(os.path.join(self.watch_path,self.config["input-file"]))))
        

     

    ### Look for the daemon into the host
    def get_daemon(self):
        log = logging.getLogger(__name__)
        try:
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

            self.daemon = daemon.format(p)
        except:
            log.error("Unable to get the daemon due to an unknown error.")
            exit(1)

    # initialize logging system
    def logging_config(self):        
        try:
            logging_config = self.config["log-config"]

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

    ### Loads the configuration json
    def read_config(self):
        try:
            config_path = os.path.realpath(CONFIG_FILENAME)
            with open(config_path) as data_file:
                self.config = json.load(data_file)
        except:
            print("ERROR: Unable to read config file {}. Please be sure the file exists and Docker has permission to read/wrtie it".format(CONFIG_FILENAME), file=sys.stderr)
            exit(1)

    # Ctrl+C handler for exiting the script    
    def set_exit_handler(self, func):
        if os.name == "nt":
            try:
                import win32api
                win32api.SetConsoleCtrlHandler(func, True)
            except ImportError:
                version = ".".join(map(str, sys.version_info[:2]))
                raise Exception("pywin32 not installed for Python " + version)
        else:
            import signal
            signal.signal(signal.SIGINT, func)
            
    # exiting the script        
    def on_exit(self, sig, func=None):        
        log = logging.getLogger(__name__)
        log.info("Cleaning up and exiting")
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)

    # constructor       
    def __init__(self):

        self.read_config()
        self.logging_config()
        self.set_exit_handler(self.on_exit)
        self.get_daemon()
        self.set_container()





    
### Entrypoint
if __name__ == "__main__":
    setup = Setup()
    
    os.environ["CORE"] = CORE_FILENAME                      # Core file with the rendering templates
    os.environ["WATCH"] = setup.watch_path                  # Where we want to monitor the file changes
    os.environ["RENDER"] = setup.render_path                # Path where the render engine is going to be working on
    os.environ["OUTPUT_NAME"] = OUTPUT_NAME                 # Filename pattern, the engine will be saving the output
    os.environ["DAEMON"] = setup.daemon                     # Engine abspath
    
    monitor = Monitor(setup.config)

    
