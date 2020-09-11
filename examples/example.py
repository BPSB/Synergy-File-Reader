#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
Our data is located in the file `example_data.txt` in the same folder. We can load it like this:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 1-2

Now `my_file` is (for all practical purposes) a list containing the individual plates in the file. In our case there is only one such plate, so it’s best to assign it to a separate variable:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 4

In such a case, it often makes sense to load the file and extract the plate in one command. The following is equivalent to the above:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 1,5

If you are familiar with Python data structures, everything else is straightforward now: Have a look at the properties and keys of `my_plate` and it should be clear how to access the information you need. If not, we proceed with a small tour:

`my_plate` has a series of properties containing information we may care about. Let’s start with `channels`:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 7

This tells us that we measured only one channel for our plate, which we called *OD:600.* We can now extract and print the times and temperatures for these measurements:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 8-11

The `my_plate.metadata` is a dictionary, which contains all sorts of tangential data for our plate, as long as it is contained in the file. For example, if we want to know the version of the software that produced our plate, we can do this as follows:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 12

However, what we usually care about is the rare data. For each well and channel, this is stored in a NumPy array. We can access it by directly indexing `my_plate`. The following commands are all equivalent, with the last only working because we only have one channel:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 14-17

Our file includes no aggregated results such as growth rates computed by the Synergy software. If it did, they would be in the dictionary `my_data.results`, each value of which is a `SynergyResult` which can be indexed like `my_plate`.

If we want to access the raw data for all wells, we can do this with the `values` function which mirrors this functionality for dictionaries. `keys` analogously gives us all well–channel combinations. In the following example, we take the first values from the time series for all wells, and compute the 10\ :sup:`th` percentile of them as a baseline for our measurements:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 19-20

The attributes `rows` and `cols` facilitate easy iterations over all rows or columns, respectively. We here compute the element-wise median of all time series in the first row (“A”), to use as a reference for comparisons:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 21

Finally, we `plot` our data. We here specify that the `baseline` we computed before shall be subtracted from all time series. Moreover, our `reference` should appear in each plot:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 23-30

The remaining arguments are hopefully self-explanatory and also explained in the documentation of `plot`. `fig` is a Matplotlib figure object with all the functionality that comes with that. For example, we can use `savefig` to export our plot to a file:

.. literalinclude:: ../examples/example.py
	:start-after: example-st\u0061rt
	:dedent: 1
	:lines: 31

And this is what our plot looks like:

.. plot:: ../examples/example.py
"""

if __name__ == "__main__":
	# example-start
	from synergy_file_reader import SynergyFile
	my_file = SynergyFile("example_data.txt")
	
	my_plate = my_file[0]
	my_plate = SynergyFile("example_data.txt")[0]
	
	print(my_plate.channels) # ['OD:600']
	channel = my_plate.channels[0]
	print(channel) # 'OD:600'
	print(my_plate.times[channel])
	print(my_plate.temperatures[channel])
	print(my_plate.metadata["Software Version"])
	
	print(my_plate["C3",channel])
	print(my_plate["c3",channel])
	print(my_plate["C",3,channel])
	print(my_plate["C3"])
	
	import numpy as np
	baseline = np.percentile( [ts[0] for ts in my_plate.values()], 10 )
	reference = np.median( [my_plate["A",col] for col in my_plate.cols], axis=0 )
	
	fig,axess = my_plate.plot(
			colours = ["red"],
			ylim = (1e-3,2), xlim = (0,30000),
			baseline = baseline,
			plot_args = {"linewidth":3},
			reference = reference,
			reference_plot_args = { "color":"black", "linewidth":1, "label":"no drug" },
		)
	fig.savefig( "example.pdf", bbox_inches="tight" )


