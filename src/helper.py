import builtins
from typing import TYPE_CHECKING, Callable, Union

from polyglot import ForeignNone, ForeignObject, interop_type

import java
import os
import time
import threading
import traceback
import profile, pstats, io
from inspect import isfunction, isclass
from datetime import datetime, timezone, timedelta

from openhab.jsr223 import TopCallStackFrame
from openhab.services import getService

from org.openhab.core.config.core import Configuration

from org.openhab.core.thing import ChannelUID as Java_ChannelUID, ThingUID as Java_ThingUID, Channel as Java_Channel, Thing as Java_Thing
from org.openhab.core.thing.link import ItemChannelLink as Java_ItemChannelLink
from org.openhab.core.automation.module.script.rulesupport.shared.simple import SimpleRule as Java_SimpleRule
from org.openhab.core.persistence.extensions import PersistenceExtensions as Java_PersistenceExtensions
from org.openhab.core.model.script.actions import Semantics as Java_Semantics

from org.openhab.core.items import Item as Java_Item, MetadataKey as Java_MetadataKey, Metadata as Java_Metadata, ItemNotFoundException as Java_ItemNotFoundException
from org.openhab.core.types import PrimitiveType as Java_PrimitiveType, UnDefType as Java_UnDefType, State as Java_State, Command as Java_Command
from org.openhab.core.library.types import DecimalType as Java_DecimalType, UpDownType as Java_UpDownType, PercentType as Java_PercentType, DateTimeType as Java_DateTimeType

from java.time import ZonedDateTime as Java_ZonedDateTime, Instant as Java_Instant
from java.lang import Object as Java_Object, Iterable as Java_Iterable, Exception as Java_Exception

from scope import RuleSupport, osgi#, RuleSimple
import scope

METADATA_REGISTRY = getService("org.openhab.core.items.MetadataRegistry")
ITEM_BUILDER_FACTORY = getService("org.openhab.core.items.ItemBuilderFactory")
ITEM_CHANNEL_LINK_REGISTRY = getService("org.openhab.core.thing.link.ItemChannelLinkRegistry")

def versiontuple(v):
    return tuple(map(int, (v.split("."))))
BUNDLE_VERSION = versiontuple(".".join(osgi.bundleContext.getBundle().getVersion().toString().split(".")[:3]))

# **** LOGGING ****
Java_LogFactory = java.type("org.slf4j.LoggerFactory")
LOG_PREFIX = "org.openhab.automation.pythonscripting"
FILENAME = NAME_PREFIX = None
if 'javax.script.filename' in TopCallStackFrame:
    FILENAME = TopCallStackFrame['javax.script.filename']
    uid = os.path.basename(FILENAME)[:-3]
else:
    # Backward compatible with openhab < 5.1
    uid = TopCallStackFrame['ctx']['ruleUID'] if 'ctx' in TopCallStackFrame and 'ruleUID' in TopCallStackFrame['ctx'] else ( TopCallStackFrame['ruleUID'] if 'ruleUID' in TopCallStackFrame else None)
if uid is not None:
    LOG_PREFIX = "{}.{}".format(LOG_PREFIX, uid)
    NAME_PREFIX = "{}".format(uid)
logger = Java_LogFactory.getLogger( LOG_PREFIX )
# *****************************************************************

__all__ = ["rule", "logger", "Registry"]

class NotFoundException(Exception):
    pass

class rule():
    def __init__(self, name: str = None, description: str = None, tags: list[str] = None, triggers: list = None, conditions: list = None, runtime_measurement: bool = True, profile_code: bool = False):
        self.name = name
        self.description = description
        self.tags = tags
        self.triggers = triggers
        self.conditions = conditions
        self.runtime_measurement = runtime_measurement
        self.profile_code = profile_code

        if isfunction(name) or isclass(name):
            self.name = None
            self(name)

    def __call__(self, clazz_or_function: Union[Callable, object]):
        proxy = self

        rule_isfunction = isfunction(clazz_or_function)
        rule_obj = clazz_or_function if rule_isfunction else clazz_or_function()

        clazz_or_function.logger = Java_LogFactory.getLogger( "{}.{}".format(LOG_PREFIX, clazz_or_function.__name__) )

        triggers = []
        if proxy.triggers is not None:
            triggers = proxy.triggers
        elif hasattr(rule_obj, "_when_triggers"):
            triggers = rule_obj._when_triggers
        elif hasattr(rule_obj, "buildTriggers") and callable(rule_obj.buildTriggers):
            triggers = rule_obj.buildTriggers()

        raw_triggers = []
        for trigger in triggers:
            raw_triggers.append(trigger.raw_trigger)

        conditions = []
        if proxy.conditions is not None:
            conditions = proxy.conditions
        elif hasattr(rule_obj, "_onlyif_conditions"):
            conditions = rule_obj._onlyif_conditions
        elif hasattr(rule_obj, "buildConditions") and callable(rule_obj.buildConditions):
            conditions = rule_obj.buildConditions()

        raw_conditions = []
        for condition in conditions:
            raw_conditions.append(condition.raw_condition)

        #register_interop_type(Java_SimpleRule, clazz)
        #subclass = type(clazz.__name__, (clazz, BaseSimpleRule,))

        # dummy helper to avoid "org.graalvm.polyglot.PolyglotException: java.lang.IllegalStateException: unknown type com.oracle.truffle.host.HostObject"
        class BaseSimpleRule(Java_SimpleRule):
            def execute(self, module, input):
                proxy.executeWrapper(rule_obj, rule_isfunction, module, input)

        name = "{}.{}".format(NAME_PREFIX, clazz_or_function.__name__) if proxy.name is None else proxy.name

        base_rule_obj = BaseSimpleRule()
        base_rule_obj.setName(name)

        if proxy.description is not None:
            base_rule_obj.setDescription(proxy.description)

        if proxy.tags is not None:
            base_rule_obj.setTags(proxy.tags)

        if len(raw_triggers) == 0:
            clazz_or_function.logger.warn("Rule '{}' has no triggers".format(name))
        else:
            base_rule_obj.setTriggers(raw_triggers)

            if len(raw_conditions) > 0:
                base_rule_obj.setConditions(raw_conditions)

            rule = RuleSupport.automationManager.addRule(base_rule_obj)

            if BUNDLE_VERSION < versiontuple("5.0.0"):
                actionConfiguration = rule.getActions().get(0).getConfiguration()
                actionConfiguration.put('type', 'application/x-python3')
                if FILENAME:
                    actionConfiguration.put('script', f"# text based rule in file: {FILENAME}")
            else:
                rule.getConfiguration().put('sourceType', 'application/x-python3')
                if FILENAME:
                    rule.getConfiguration().put('source', f"# text based rule in file: {FILENAME}")

            clazz_or_function.logger.info("Rule '{}' initialised".format(name))

        return rule_obj

    def executeWrapper(self, rule_obj: Union[Callable, object], rule_isfunction: bool, module: dict[str, any], input: dict[str, any]):
        try:
            start_time = time.perf_counter()

            if self.profile_code:
                pr = profile.Profile()
                pr.runctx('func(module, input)', {'module': module, 'input': input, 'func': rule_obj if rule_isfunction else rule_obj.execute }, {})
                s = io.StringIO()
                ps = pstats.Stats(pr, stream=s).sort_stats('cumulative')
                ps.print_stats()
                rule_obj.logger.info(s.getvalue())
            else:
                rule_obj(module, input) if rule_isfunction else rule_obj.execute(module, input)

            if self.runtime_measurement:
                try:
                    if input['event'].getType().startswith("Item"):
                        msg_details = " [Item: {}]".format(input['event'].getItemName())
                    elif input['event'].getType().startswith("Group"):
                        msg_details = " [Group: {}]".format(input['event'].getItemName())
                    elif input['event'].getType().startswith("Thing"):
                        msg_details = " [Thing: {}]".format(input['event'].getThingUID())
                    else:
                        msg_details = " [Other: {}]".format(input['event'].getType())
                except KeyError:
                    msg_details = ""
                rule_obj.logger.info("Rule executed in " + "{:6.1f}".format(round( ( time.perf_counter() - start_time ) * 1000, 1 )) + " ms" + msg_details)
        except Exception as e:
            rule_obj.logger.error("Rule execution failed: " + builtins.__formatTraceback__(e))

class _Tracing():
    @staticmethod
    def processMissingAttribute(cls: str, name: str):
        raise builtins.__wrapException__(AttributeError("Java instance of '{}' has no attribute '{}'".format(cls, name)), 2)

    @staticmethod
    def getAttributeWrapper(attr: any, *args: any):
        try:
            return attr(*args)
        except TypeError as e:
            if str(e) == "invalid instantiation of foreign object":
                raise builtins.__wrapException__(AttributeError("One of your function parameters does not match the required value type."), 2)
            raise e

    @staticmethod
    def foreignNoneFallback(self, name: str):
        raise builtins.__wrapException__(AttributeError("None object has no attribute '{}'".format(name)), 1)

    @staticmethod
    def javacall(function: Callable):
        def wrap(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Java_Exception as e:
                raise builtins.__wrapException__(AttributeError(e),1)
        return wrap

ForeignNone.__getattr__ = _Tracing.foreignNoneFallback

class _JavaCallProxy:
    def __init__(self, proxy: Java_Object, callback: Callable):
        self.proxy = proxy
        self.callback = callback

    def __getattr__(self, name: str):
        try:
            attr = getattr(self.proxy, name)
            if callable(attr) and java.is_function(attr):
                return lambda *args, **kwargs: _Tracing.getAttributeWrapper( attr, *(self.callback(*args)) )
            return attr
        except AttributeError as e:
            _Tracing.processMissingAttribute(self.proxy, name)

@interop_type(Java_Object)
class Object:
    def __getattribute__(self, name: str):
        attr = super().__getattribute__(name)
        if callable(attr) and java.is_function(attr):
            return lambda *args, **kwargs: _Tracing.getAttributeWrapper( attr, *args )
        return attr

    def __getattr__(self, name: str):
        _Tracing.processMissingAttribute(self.getClass(), name)

@interop_type(Java_Instant)
class Instant(datetime):
    def __new__(cls, year: int, month: int = None, day: int = None, hour: int = 0, minute: int = 0, second: int = 0,
                microsecond=0, tzinfo=None, *, fold=0):
        return datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second, microsecond=microsecond, tzinfo=tzinfo, fold=fold)

    def __getattribute__(self, name: str):
        #print(name)
        match name:
            case "_year": return super().getYear()
            case "_month": return super().getMonthValue()
            case "_day": return super().getDayOfMonth()
            case "_hour": return super().getHour()
            case "_minute": return super().getMinute()
            case "_second": return super().getSecond()
            case "_microsecond": return int(super().getNano() / 1000)
            case "_tzinfo": return None
            case "_hashcode": return -1
            case "_fold": return 0
        return super().__getattribute__(name)

    def __hash__(self):
        return hash(self._getstate())

@interop_type(Java_ZonedDateTime)
class DateTime(Instant):
    def __getattribute__(self, name: str):
        match name:
            case "_tzinfo": return timezone(timedelta(seconds=super().getOffset().getTotalSeconds()), super().getZone().getId())
        return super().__getattribute__(name)

@interop_type(Java_Item)
class Item(Java_Item if TYPE_CHECKING else object):
    @_Tracing.javacall
    def postUpdate(self, state: Union[Java_State, int, float, str]):
        scope.events.postUpdate(self, state)

    def postUpdateIfDifferent(self, state: Union[Java_State, int, float, str]) -> bool:
        if not Item._checkIfDifferent(self.getState(), state):
            return False
        self.postUpdate(state)
        return True

    @_Tracing.javacall
    def sendCommand(self, command: Union[Java_State, int, float, str]):
        scope.events.sendCommand(self, command)

    def sendCommandIfDifferent(self, command: Union[Java_State, int, float, str]) -> bool:
        if not Item._checkIfDifferent(self.getState(), command):
            return False
        self.sendCommand(command)
        return True

    @_Tracing.javacall
    def getThings(self) -> list[Java_Thing]:
        return ITEM_CHANNEL_LINK_REGISTRY.getBoundThings(self.getName())

    @_Tracing.javacall
    def getChannels(self) -> list[Java_Channel]:
        return list(map(lambda uid: Registry.getChannel(uid.getAsString()), ITEM_CHANNEL_LINK_REGISTRY.getBoundChannels(self.getName())))

    @_Tracing.javacall
    def getChannelUIDs(self) -> list[str]:
        return ITEM_CHANNEL_LINK_REGISTRY.getBoundChannels(self.getName())

    @_Tracing.javacall
    def getChannelLinks(self) -> list[Java_ItemChannelLink]:
        return ITEM_CHANNEL_LINK_REGISTRY.getLinks(self.getName())

    @_Tracing.javacall
    def linkChannel(self, channel_uid: str, link_config: dict[str, str] = {}) -> Java_ItemChannelLink:
        link = Java_ItemChannelLink(self.getName(), Java_ChannelUID(channel_uid), Configuration(link_config))
        links = [l for l in self.getLinks() if l.getLinkedUID().getAsString() == channel_uid]
        if len(links) > 0:
            if not links[0].getConfiguration().equals(link.getConfiguration()):
                ITEM_CHANNEL_LINK_REGISTRY.update(link)
        else:
            ITEM_CHANNEL_LINK_REGISTRY.add(link)
        return link

    @_Tracing.javacall
    def unlinkChannel(self, channel_uid: str) -> Java_ItemChannelLink:
        links = [l for l in self.getLinks() if l.getLinkedUID().getAsString() == channel_uid]
        if len(links) > 0:
            ITEM_CHANNEL_LINK_REGISTRY.remove(links[0].getUID())
            return links[0]
        raise NotFoundException("Link {} not found".format(channel_uid))

    def getPersistence(self, service_id: str = None) -> 'ItemPersistence':
        return ItemPersistence(self, service_id)

    def getSemantic(self) -> 'ItemSemantic':
        return ItemSemantic(self)

    def getMetadata(self) -> 'ItemMetadata':
        return ItemMetadata(self)

    @staticmethod
    def buildSafeName(s: str):
        # Remove quotes and replace non-alphanumeric with underscores
        return ''.join([c if c.isalnum() else '_' for c in s.replace('"', '').replace("'", '')])

    @staticmethod
    def _checkIfDifferent(current_state: any, new_state: any):
        if not java.instanceof(current_state, Java_UnDefType):
            if java.instanceof(current_state, Java_PercentType):
                if isinstance(new_state, str):
                    if new_state == "UP":
                        new_state = 0
                    if new_state == "DOWN":
                        new_state = 100
                elif java.instanceof(new_state, Java_UpDownType):
                    new_state = (0 if new_state.toFullString() == "UP" else 100)

            if java.instanceof(new_state, Java_PrimitiveType):
                new_state = new_state.toFullString()
            elif isinstance(new_state, datetime):
                new_state = new_state.isoformat()
            else:
                new_state = str(new_state)

            if java.instanceof(current_state, Java_PrimitiveType):
                current_state = current_state.toFullString()
            elif isinstance(current_state, datetime):
                current_state = current_state.isoformat()
            else:
                current_state = str(current_state)

            return current_state != new_state
        return True

class ItemSemantic(Java_Semantics if TYPE_CHECKING else _JavaCallProxy):
    def __init__(self, item: Item):
        super().__init__(Java_Semantics, lambda *args: tuple([item]) + args)

class ItemPersistence(Java_PersistenceExtensions if TYPE_CHECKING else _JavaCallProxy):
    def __init__(self, item: Item, service_id: str = None):
        super().__init__(Java_PersistenceExtensions, lambda *args: tuple([item]) + args + tuple([] if service_id is None else [service_id]) )

    def getStableMinMaxState(self, time_slot: int, end_time: datetime = None) -> tuple[Java_DecimalType,Java_DecimalType,Java_DecimalType]:
        current_end_time = datetime.now().astimezone() if end_time is None else end_time
        min_time = current_end_time - timedelta(seconds=time_slot)

        min_value = max_value = None
        value = duration = 0.0

        entry = self.persistedState(current_end_time)

        while True:
            currentStartTime = entry.getTimestamp()

            if currentStartTime < min_time:
                currentStartTime = min_time

            _duration = ( currentStartTime - current_end_time ).total_seconds()
            _value = entry.getState().doubleValue()

            if min_value == None or min_value > _value:
                min_value = _value
            if max_value == None or max_value < _value:
                max_value = _value

            duration = duration + _duration
            value = value + ( _value * _duration )

            current_end_time = currentStartTime - timedelta(microseconds=1)
            if current_end_time < min_time:
                break

            entry = self.persistedState(current_end_time)

        return [ Java_DecimalType(value / duration), Java_DecimalType(min_value), Java_DecimalType(max_value) ]

    def getStableState(self, time_slot: int, end_time: datetime = None) -> Java_DecimalType:
        value, _, _ = self.getStableMinMaxState(time_slot, end_time)
        return value

class ItemMetadata():
    def __init__(self, item):
        self.item = item

    @_Tracing.javacall
    def get(self, namespace: str) -> Java_Metadata:
        return METADATA_REGISTRY.get(Java_MetadataKey(namespace, self.item.getName()))

    @_Tracing.javacall
    def set(self, namespace: str, value, configuration=None) -> Java_Metadata:
        if self.get(namespace) == None:
            return METADATA_REGISTRY.add(Java_Metadata(Java_MetadataKey(namespace, self.item.getName()), value, configuration))
        else:
            return METADATA_REGISTRY.update(Java_Metadata(Java_MetadataKey(namespace, self.item.getName()), value, configuration))

    @_Tracing.javacall
    def remove(self, namespace: str) -> Java_Metadata:
        return METADATA_REGISTRY.remove(Java_MetadataKey(namespace, self.item.getName()))

    @_Tracing.javacall
    def removeAll(self):
        METADATA_REGISTRY.removeItemMetadata(self.item.getName())

class Registry():
    @staticmethod
    def getThings() -> list[Java_Thing]:
        return scope.things.getAll()

    @staticmethod
    @_Tracing.javacall
    def getThing(uid: str) -> Java_Thing:
        thing = scope.things.get(Java_ThingUID(uid))
        if thing is None:
            raise builtins.__wrapException__(NotFoundException("Thing {} not found".format(uid)),2)
        return thing

    @staticmethod
    @_Tracing.javacall
    def getChannel(uid: str) -> Java_Channel:
        channel = scope.things.getChannel(Java_ChannelUID(uid))
        if channel is None:
            raise builtins.__wrapException__(NotFoundException("Channel {} not found".format(uid)),2)
        return channel

    @staticmethod
    @_Tracing.javacall
    def getItemState(item_name: str, default: Java_PrimitiveType = None) -> Java_PrimitiveType:
        if not isinstance(item_name, str):
            raise builtins.__wrapException__(Exception("Unsupported parameter type {}".format(type(item_name))),2)
        state = scope.items.get(item_name)
        if state is None:
            raise builtins.__wrapException__(NotFoundException("Item state for {} not found".format(item_name)),2)
        if default is not None and java.instanceof(state, Java_UnDefType):
            state = default
        return state

    @staticmethod
    @_Tracing.javacall
    def getItem(item_name: str) -> Item:
        if not isinstance(item_name, str):
            raise builtins.__wrapException__(Exception("Unsupported parameter type {}".format(type(item_name))),2)
        try:
            return scope.itemRegistry.getItem(item_name)
        except Java_ItemNotFoundException:
            raise builtins.__wrapException__(NotFoundException("Item {} not found".format(item_name)),2)

    @staticmethod
    def resolveItem(item_or_item_name: Union[Item, str]) -> Item:
        if isinstance(item_or_item_name, Item):
            return item_or_item_name
        return Registry.getItem(item_or_item_name)

    @staticmethod
    @_Tracing.javacall
    def removeItem(item_name: str, recursive: bool = False) -> Item:
        if not isinstance(item_name, str):
            raise builtins.__wrapException__(Exception("Unsupported parameter type {}".format(type(item_name))),2)
        try:
            item = scope.itemRegistry.getItem(item_name)
            scope.itemRegistry.remove(item_name, recursive)
            return item
        except Java_ItemNotFoundException:
            raise builtins.__wrapException__(NotFoundException("Item {} not found".format(item_name)),2)

    @staticmethod
    @_Tracing.javacall
    def addItem(item_name: str, item_type: str, item_config: dict[str, str] = {}) -> Item:
        item = Registry._createItem(item_name, item_type, item_config)
        scope.itemRegistry.add(item)
        return Registry.getItem(item_name)

    @staticmethod
    def _createItem(item_name: str, item_type: str, item_config: dict[str, str] = {}) -> Item:
        item_name = Item.buildSafeName(item_name)

        base_item = None
        if item_type == 'Group' and 'giBaseType' in item_config:
            base_item = ITEM_BUILDER_FACTORY.newItemBuilder(item_config['giBaseType'], item_name + '_baseItem').build()
        if item_type != 'Group':
            item_config['groupFunction'] = None

        if 'tags' not in item_config:
            item_config['tags'] = []
        item_config['tags'].append("_DYNAMIC_")

        try:
            builder = ITEM_BUILDER_FACTORY.newItemBuilder(item_type, item_name) \
                .withCategory(item_config.get('category')) \
                .withLabel(item_config.get('label')) \
                .withTags(item_config['tags'])

            if 'groups' in item_config:
                builder = builder.withGroups(item_config['groups'])

            if base_item is not None:
                builder = builder.withBaseItem(base_item)
            if item_config.get('groupFunction') is not None:
                builder = builder.withGroupFunction(item_config['groupFunction'])

            item = builder.build()
            return item
        except Exception as e:
            logger.error('Failed to create Item: {}'.format(e))
            raise
