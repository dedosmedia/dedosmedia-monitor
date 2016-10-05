#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
#from watchdog.observers import Observer
from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
from os.path import expanduser
from shutil import copyfile
import time
from os import rename
import os, sys
import json
import subprocess
import gzip
import time
import zmq
import logging
import logging.config
import signal

### Global variables
context = zmq.Context()
socket = context.socket(zmq.PUB)
config = json.loads('[]')   #default json, overwritten with config.json

### reading the dynamic library

input = gzip.GzipFile(os.environ["CORE"], 'rb')
stream = input.read()
input.close()


   
class Watcher:

    def __init__(self):
        self.observer = Observer()

    def run(self):
        global config
        try:
            watch_file = os.path.realpath(os.path.join(os.environ["WATCH"],config["input-file"]))
            log = logging.getLogger(__name__)
            log.info("Monitoring for file: %s" %os.path.abspath(watch_file))
        except Error as error:
            log.error("Error trying to monitor the file {}".format(error))
        event_handler = Handler()

        self.observer.schedule(event_handler, os.path.dirname(os.path.abspath(watch_file)), recursive=False)
        try:
            self.observer.start()
        
            while True:
                time.sleep(5)
        except Exception as error:
            log.error("The monitored folder does not exist. Please fix it.")
        except:
            self.observer.stop()
            log.error("ERROR: Unknnown error in observer.")
        self.observer.join()


class Handler(FileSystemEventHandler):
    global config


    @staticmethod
    def on_any_event(event):
        log = logging.getLogger(__name__)
        log.info(os.path.abspath(os.path.normpath(event.src_path)))
        watch_file = os.path.realpath(os.path.join(os.environ["WATCH"],config["input-file"]))
        isWatchedFile = os.path.normpath(watch_file) == os.path.normpath(event.src_path)
        log.info("--> %s, %s, %s -- %s" %(isWatchedFile, event.event_type, os.path.normpath(watch_file),os.path.normpath(event.src_path) ))
        if event.is_directory:
            return None
        elif (event.event_type == 'created') and isWatchedFile:
            # Take any action here when a file is first created.
            log.info(">>>>> File %s has been %s"  % (event.src_path, event.event_type))
            render()


### Send render configuration to the Host
def render():
    global config
    global socket

    try:
        try:
            devnull = None
            config["error"]
        except KeyError as error:
            devnull = open(os.devnull, 'w')
        
        try:            
            output = file(os.path.join(os.environ["RENDER"],"masterCC.aepx"), 'wb')
        except IOError as error:
            log.error("Error, some needed files are missing. AEPX not found.")
            return
        #print("Writing aepx :: {}".format(output))
        output.write(stream)
        output.close()

       
        src = os.path.realpath(os.path.join(os.environ["WATCH"],config["input-file"]))
        dst = os.path.join(os.environ["RENDER"],'input','input0.jpg')

        #print("{} - {}".format(src,dst))
        copyfile(src, dst)
        
        args = [  
            '-project', 
            "{}/masterCC.aepx".format(os.environ["HOST_RENDER_PATH"]),
            '-comp',
            config['image-size'],
            '-OMtemplate',
            'jpg',
            '-output',
            "{}/{}".format(os.environ["HOST_RENDER_PATH"],os.environ["OUTPUT_NAME"].format("[%23]")),#output_file.format("[%23]"),
            '-s',
            '0', 
            '-e',
            '0',
            '-i',
            '1',
            '-close',
            'DO_NOT_SAVE_CHANGES',
            '-reuse',
            '-continueOnMissingFootage']

        socket.send_json({'command':'render', 'args':json.dumps(args)})

        

       
    except Exception as error:
        log.error("Render Error, please check the configuration %s" %error)
        os.remove(output.name)
    except subprocess.CalledProcessError as error:
        log.error("Error in subprocess. Error Code: %s " %error.returncode)
        os.remove(output.name)
        return error.returncode


### ZMQ publisher
def zmq_publisher():
    global socket
    socket.bind("tcp://0.0.0.0:{}".format(os.environ["PORT"]))
    

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
        log.info("Monitor: Logging successfully initialized")
    except:
        print("Monitor: Unable to initialize logging", file=sys.stderr)
        raise

### start daemon to watch file changes
def watch_folder():
    w = Watcher()
    w.run()

def main():
    global config
    print
    ### read config file
    try:
        config_path = os.path.realpath(os.environ["CONFIG"])
        with open(config_path) as data_file:
            config = json.load(data_file)
    except:
        print("ERROR: Unable to read config file {}".format(os.environ["CONFIG"]), file=sys.stderr)

    logging_config()
    zmq_publisher()
    watch_folder();

def set_exit_handler(func):
    signal.signal(signal.SIGTERM, func)
        
def on_exit(sig, func=None):
    global container_id
    global socket
    global context
    global cli
    
    log = logging.getLogger(__name__)
    log.info("Cleaning up and exiting the monitor")
  
    socket.close()
    context.term()
    try:
        sys.exit(0)
    except SystemExit:
        os._exit(0)

### entrypoint
if __name__ == '__main__':
    set_exit_handler(on_exit)
    main()
   
