## Migration Guide

the goal of this document is to collect dropin replacements if you migrate from the legacy jython based helper library to this new helper library

### JSR223 Scope

In jython, almost everythig related to the [jsr223 context](https://www.openhab.org/docs/configuration/jsr223.html) was injected in the global script frame. This means constants like ['ON', 'OFF', UP', 'DOWN', 'NULL' etc](https://www.openhab.org/docs/configuration/jsr223.html#default-preset-importpreset-not-required) was available without any additional import. The negative side effect was that the global scope was overbloated with a lot of variables, regardless if they are needed or not.

to have the same behavior again, you should add an import statement on top like

```python
from scope import *
```

or

```python
import scope
 
# scope.ON
```

or just import variables you really need

```python
from scope import ON, OFF, UP, DOWN
```

### Logging

legacy syntax

```python
from core.log import logging, LOG_PREFIX
log = logging.getLogger("{}.action_example".format(LOG_PREFIX))
log.info("Testmessage")
```

new syntax

```python
from openhab import logging
logging.info("Testmessage")
```

### Rules

The @rule decorator can be used unchanged. The name as a first attribute is completly optional. If not provided, the class or function name is used as the rule name.

legacy syntax

```python
from core.rules import rule
from core.triggers import when

@rule("Example Channel event rule (decorators)", description="This is an example rule that is triggered by the sun setting", tags=["Example", "Astro"])
@when("Channel astro:sun:local:set#event triggered START")
def channelEventExampleDecorators(event):
    channelEventExampleDecorators.log.info("Sunset triggered")
```

new syntax

```python
from openhab import rule
from openhab.triggers import when

@rule("Example Channel event rule (decorators)", description="This is an example rule that is triggered by the sun setting", tags=["Example", "Astro"])
@when("Channel astro:sun:local:set#event triggered START")
def channelEventExampleDecorators(event):
    channelEventExampleDecorators.logger.info("Sunset triggered")
```

or

```python
from openhab import rule
from openhab.triggers import when

@rule("Example Channel event rule (decorators)", description="This is an example rule that is triggered by the sun setting", tags=["Example", "Astro"])
@when("Channel astro:sun:local:set#event triggered START")
class ChannelEventExampleDecorators():
    def execute(self, module, event):
        self.logger.info("Sunset triggered")
```

or

```python
from openhab import rule
from openhab.triggers import ChannelEventTrigger

@rule(
    triggers=[ ChannelEventTrigger("astro:sun:local:set#event", "START") ],
    description="This is an example rule that is triggered by the sun setting", 
    tags=["Example", "Astro"]
)
class ChannelEventExampleDecorators():
    def execute(self, module, event):
        self.logger.info("Sunset triggered")
```

### Get an Item, Things, Channel

legacy syntax

```python
itemRegistry.getItem("Item1")
things.getThing("hue:bridge-api2:default")
things.getChannel("astro:sun:local:set#event")
```

new syntax
```python
from openhab import Registry

Registry.getItem("Item1")
Registry.getThing("hue:bridge-api2:default")
Registry.getChannel("astro:sun:local:set#event")
```


### import changes

It is mostly a rename of "core" to "openhab". Additionaly the order of parameters in Trigger classes are changed. "state" and "previous_status" is swapped. If you already use named parameters, you you don't need to change anything.

legacy syntax (e.g)

```python
from core.actions import Exec
from core.triggers import ItemCommandTrigger
```

new syntax
```python
from openhab.actions import Exec
from openhab.actions import ItemCommandTrigger
```
