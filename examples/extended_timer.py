from openhab import rule,
from openhab.triggers import ItemStateChangeTrigger

import threading

class Timer(threading.Timer):
    @staticmethod
    def createTimeout(duration, callback, args =[], kwargs ={}, old_timer = None, max_count = 0 ):
        if old_timer != None:
            old_timer.cancel()
            max_count = old_timer.max_count

        max_count = max_count - 1
        if max_count == 0:
            callback(*args, **kwargs)
            return None

        timer = Timer(duration, callback, args, kwargs )
        timer.start()
        timer.max_count = max_count
        return timer


#Below is a complex example of 2 sensor values that are expected to be transmitted in a certain time window (e.g. one after the other).

#After the first state change, the timer waits 5 seconds, before it updates the final target value.
#If the second value arrives before this time frame, the final target value is updated immediately.

@rule(
    triggers = [
        ItemStateChangeTrigger("Room_Temperature_Value"),
        ItemStateChangeTrigger("Room_Humidity_Value")
    ]
)
class UpdateInfo:
    def __init__(self):
        self.update_timer = None

    def updateInfoMessage(self):
        msg = "{}{} °C, {} %".format(Registry.getItemState("Room_Temperature_Value").format("%.1f"), Registry.getItemState("Room_Temperature_Value").format("%.0f"))
        Registry.getItem("Room_Info").postUpdate(msg)
        self.update_timer = None

    def execute(self, module, input):
        self.update_timer = Timer.createTimeout(5, self.updateInfoMessage, old_timer = self.update_timer, max_count=2 )
