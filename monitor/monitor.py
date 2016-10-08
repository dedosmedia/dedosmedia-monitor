#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function
from watchdog.observers import Observer
#from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler
import shutil
import time
import os
import subprocess
import gzip
import time
import logging


   
class Watcher:

    def __init__(self):
        self.observer = Observer()

    def run(self, config, stream):
        self.config = config
        self.stream = stream
        try:
            log = logging.getLogger(__name__)
            self.watch_file = os.path.realpath(os.path.join(os.environ["WATCH"],self.config["input-file"])) 
            log.info("Monitoring for file: %s" %os.path.abspath(self.watch_file))
        except Exception as error:
            log.error("Error trying to monitor the file {}".format(error))

        self.event_handler = FileSystemEventHandler()
        self.event_handler.on_any_event = self.on_any_event

        self.observer.schedule(self.event_handler, os.path.dirname(os.path.abspath(self.watch_file)), recursive=False)
        try:
            self.observer.start()
            while True:
                time.sleep(5)
        except Exception as error:
            log.error("The monitored folder does not exist. Please fix it.")
            self.observer.stop()
            log.error("ERROR: Unknnown error in observer.")
        self.observer.join()

    def on_any_event(self, event):
        log = logging.getLogger(__name__)
        #log.info(os.path.abspath(os.path.normpath(event.src_path)))
        isWatchedFile = os.path.normpath(self.watch_file) == os.path.normpath(event.src_path)
        #log.info("--> %s, %s, %s -- %s" %(isWatchedFile, event.event_type, os.path.normpath(self.watch_file),os.path.normpath(event.src_path) ))
        if event.is_directory:
            return None
        elif (event.event_type == 'created') and isWatchedFile:
            # Take any action here when a file is first created.
            log.info("[CHANGE DETECTED] File %s has been %s"  % (event.src_path, event.event_type))
            self.render()

    ### Send render configuration to the Host
    def render(self):
        log = logging.getLogger(__name__)
        try:
            try:
                devnull = None
                self.config["error"]
            except KeyError as error:
                devnull = open(os.devnull, 'w')
            
            try:            
                output = file(os.path.realpath(os.path.join(os.environ["RENDER"],"masterCC.aepx")), 'wb')
            except IOError as error:
                log.error("Error, some needed files are missing. AEPX not found.")
                return
            #print("Writing aepx :: {}".format(output))
            output.write(self.stream)
            output.close()


            src = os.path.realpath(os.path.join(os.environ["WATCH"],self.config["input-file"]))
            dst = os.path.join(os.environ["RENDER"],'input','input0.jpg')

            #print("{} - {}".format(src,dst))
            shutil.copyfile(src, dst)
            
            args = [
                os.environ["DAEMON"],
                '-project', 
                output.name,
                '-comp',
                self.config['image-size'],
                '-OMtemplate',
                'jpg',
                '-output',
                "{}/{}".format(os.environ["RENDER"],os.environ["OUTPUT_NAME"].format("[%23]")),
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

            try:
                devnull = None
                self.config["error"]
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
                    src = os.path.join(os.environ["RENDER"],os.environ["OUTPUT_NAME"].format("0"))
                    dst = os.path.normpath(os.path.join(os.environ["WATCH"],self.config["output-subfolder"],self.config['output-file']))
                    shutil.move( src, dst)
                except OSError as error:
                    log.warning("WARNING: moving file {}. Retrying.".format(error))
                    os.remove(dst)
                    shutil.move(src,dst)
                    
                log.info("(((( DONE ))))))) - Monitoring again.")
               
                ## remove the aepx
                os.remove(args[2])
                
            except subprocess.CalledProcessError as error:
                log.error("ERROR: rendering process failed with code {}".format(error))
        except Exception as error:
            log.error("Render Error, please check the configuration %s" %error)
            os.remove(output.name)
        except subprocess.CalledProcessError as error:
            log.error("Error in subprocess. Error Code: %s " %error.returncode)
            os.remove(output.name)
            return error.returncode

class Monitor:

    # Constructor, real entry point
    def __init__(self, config):
        self.config = config
        self.read_core()
        self.watch_folder()
        
    def read_core(self):
        input = gzip.GzipFile(os.environ["CORE"], 'rb')
        self.stream = input.read()
        input.close()
        
    def watch_folder(self):
        w = Watcher()
        w.run(self.config, self.stream)
 


### fake entrypoint
if __name__ == '__main__':
    print("Can not be called as a script")
    pass
    
