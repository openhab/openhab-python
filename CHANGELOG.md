## UPCOMMING

* added scope object (for details check https://github.com/HolgerHees/openhab-python?tab=readme-ov-file#module-scope)
* add import wrapper 
* cleanups and minor helper lib api changes
* added IntercalCondition to triggers
* use OSGI-ified version of polyglot (this fixes https://github.com/openhab/openhab-addons/issues/18054 in openhab >= 5)

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
