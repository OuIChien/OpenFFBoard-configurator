from os import path
from functools import wraps
import sys
import time

from PyQt6.QtCore import QObject,QTimer

RESPATH = "res"

def res_path(file,respath=RESPATH):
    if getattr(sys, 'frozen',False) and hasattr(sys, '_MEIPASS'):
        return path.join(sys._MEIPASS,respath,file)
    return path.join(respath,file)

# Parses a classchooser reply into a list of classes and a dict to translate the class ID to (list index,name)
def classlistToIds(dat):
    classes = []
    idToIdx = {}
    if(dat):
        n=0
        for c in dat.split("\n"):
            if(c):
                id,creatable,name = c.split(":",2)
                idToIdx[int(id)] = (n,name)
                classes.append([int(id),name,bool(creatable != "0")])
                n+=1
    return (idToIdx,classes)

def updateClassComboBox(combobox,ids,classes,selected = None):
    """Populates a combobox with entries from a parsed classchooser reply"""
    combobox.clear()
    if(selected != None):
        selected = int(selected)
    for c in classes:
        creatable = c[2] or (selected == int(c[0]))
        combobox.addItem(c[1])
        combobox.model().item(ids[c[0]][0]).setEnabled(creatable)
    
    if(selected in ids and combobox.currentIndex() != ids[selected][0]):
        combobox.setCurrentIndex(ids[selected][0])

def updateListComboBox(combobox,reply,entrySep=',',dataSep=':',lookup = None,dataconv = None,labelconv = None):
    """Populates a combobox with entries formatted as Entrylabel<datasep>data<entrysep>..."""
    combobox.clear()
    if lookup != None:
        lookup.clear()
    i = 0
    for s in reply.split(entrySep):
        if not s:
            continue # empty
        e = s.split(dataSep)
        data = e[1]
        label = e[0]
        if dataconv != None:
            data = dataconv(data)
        if labelconv != None:
            label = labelconv(label)
        combobox.addItem(label,data)
        if lookup != None:
            lookup[data] = i
        i += 1

def splitListReply(reply,itemdelim = ':', entrydelim = '\n'):
    """Splits a reply in default format into a list of lists"""
    return [ line.split(itemdelim) for line in reply.split(entrydelim) if line]


def qtBlockAndCall(object : QObject,function,value):
    object.blockSignals(True)
    function(value)
    object.blockSignals(False)

def throttle(ms):
    """
    Decorator that throttles the execution of a function.
    The function will be called immediately if enough time has passed since the last call.
    Otherwise, it will be delayed until the timeout expires.
    """
    def decorator(fn):
        # We store the timer and last call time in the closure of the decorator
        # But we must ensure the timer is created after QApplication is initialized.
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Try to get or create a timer for this specific instance (if it's a method)
            # or a global one if it's a regular function.
            instance = args[0] if args and isinstance(args[0], QObject) else fn
            timer_attr = f"_throttle_timer_{fn.__name__}"
            
            if not hasattr(instance, timer_attr):
                timer = QTimer(instance if isinstance(instance, QObject) else None)
                timer.setSingleShot(True)
                setattr(instance, timer_attr, timer)
                setattr(instance, f"_throttle_last_call_{fn.__name__}", 0)
            
            timer = getattr(instance, timer_attr)
            
            def call():
                setattr(instance, f"_throttle_last_call_{fn.__name__}", time.time())
                fn(*args, **kwargs)
            
            now = time.time()
            last_call = getattr(instance, f"_throttle_last_call_{fn.__name__}")
            time_since_last_call = now - last_call

            # Call immediately if last call is older than timeout
            if time_since_last_call > ms/1000:
                if timer.isActive():
                    timer.stop()
                return call()

            else: # delay execution
                if timer.isActive():
                    timer.stop()

                # Disconnect previous call
                try: timer.timeout.disconnect()
                except Exception: pass

                # Connect timer
                timer.timeout.connect(call)
                timer.setInterval(ms)
                timer.start()     
        return wrapper
    return decorator

# Splits a reply in the format "name:value,name2:value2"... into a dict
def map_infostring(repl,type=float):
    return{key:type(value) for (key,value) in [entry.split(":") for entry in repl.split(",")]}