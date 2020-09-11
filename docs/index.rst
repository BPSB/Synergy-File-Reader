Synergy File Reader for Python
==============================

This module allows you to read text files produced by Synergy plate readers in Python using appropriate Python data structures.

Example
-------

.. automodule:: example

.. .. plot:: ../examples/example.py
..    :include-source:

Preparing Files
---------------

The Synergy software allows you to export files in various different layouts and control all sorts of details as to what information should be included in the file. As long as the included information is not ambiguous, this module should be able to read it – if not, `tell me <https://github.com/BPSB/synergy_file_reader/issues>`_.

If you already exported your files and did not choose for a minimal format, just try and see whether they can be loaded. If want to make sure that your file is readable and contains all information, do the following:

* Choose *Automatic* content.
* Whenever you have the option to *Include* something, do so.
* Use *tables* and not *matrices* for everything. (The main problem of the latter is that temperature information is lost.)
* Use *Tab* as a separator. (The other separators will probably work fine, but I am not sure that they do not lead to ambiguities.)

Under the Hood
--------------

If anybody cares, this module uses trial-and-error parsing. For every type of data block, there is a parser, which throws an error if fed with data that does not match the format of the type of data block. To parse a file, all of these parsers are applied one by one until one doesn’t throw an error, which is then taken to reflect the true structure of the data. This process is then repeated with the remainder of the file until there are no more lines left.

This makes the parser rather flexible to expand, but also makes it impossible to pinpoint where exactly the parsing fails. A file simply becomes unparsable once it contains a data block for which all of the implemented parsers fail.

Data Structure
--------------

`SynergyFile` is a collection of plates, each of which is a `SynergyPlate`. `SynergyPlate` inherits from `SynergyResult`, which is used for the raw data. The `results` of a `SynergyPlate` are also of the type `SynergyResult`.

Command Reference
-----------------

.. automodule:: _synergy_file_reader
	:members: SynergyResult, SynergyPlate, SynergyFile

