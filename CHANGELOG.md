## UPCOMMING

* fix script unload/cleanup
* update to graalpy 24.2.0 (openhab5/jdk21 only, openhab4/jdk17 stays with graalpy 24.1.2)
* simplified createTimer implementation
* helperlib fix to support upcomming graalpy 24.2.0
* code cleanups and refactorings based on feedback and code reviews

## 24.02.2025 18:06

* script context cleanup/close fix for compiled scripts (e.g. transformation scripts)
* log prefix for UI based and transformation scripts fixed
* logging cleanup and simplification

## 23.02.2025 20:57

* add scope, Registry and logger auto injected for UI based rules

## 23.02.2025 12:02

* added scope object and import wrapper
  * for details check [here](https://github.com/HolgerHees/openhab-python/tree/main?tab=readme-ov-file#module-scope)
* added IntervalCondition to triggers
* cleanup and minor helper lib api changes
* cleanup and simplification of helper lib deployment (no hardcoded filenames anymore)
* use OSGI-ified version of polyglot in openhab 5 (this fixes openhab/openhab-addons#18054 in openhab >= 5)
* migrate openhab helper lib into his [own repository](https://github.com/HolgerHees/openhab-python)
  * This makes it easier to decouple release cycles between openhab and helper lib

## 06.02.2025 07:30

* fixed memory leak on rule reloading (old script engine is properly closed)
* fixed tranformation service ‘PY3’
* fixed log prefix
* fixed lifecycleTracker
* cleanups

## 03.02.2025 17:34

* fixed postUpdate, postUpdateIfDifferent, sendCommand and sendCommandIfDifferent for openhab value types like UP/DOWN etc)

## 03.02.2025 08:30

* code cleanup of internal trigger validation
* various helper lib code cleanups
* added Registry.setItemMetadata and Registry.removeItemMetadata
* improved README.md

## 02.02.2025 20:26

* Fixed “Run Now” - UI in 4.3+

## 27.01.2025 08:58

* rule decorator for functions in addition to classes to allow much simpler rules
* allow import of script modules in addition to lib modules
* fixes for WebUI based rules (currently still not working because of another major bug)
* internal graal binding cleanups and simplifications
* cleanups in triggers helper module

## 23.01.2025 12:08

* added “when” and “onlyif” decorator support
* Item.getPersistance renamed to Item.getPersistence
* fixed TimeOfDayTrigger and DateTimeTrigger

## 22.01.2025 10:58

* initial release
