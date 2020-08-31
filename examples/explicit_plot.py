from synergy_file_reader import SynergyFile
import numpy as np
from matplotlib.pyplot import subplots

my_plate = SynergyFile("example_data.txt")[0]

baseline = np.percentile([ts[0] for ts in my_plate.data.values()],10)

channel = "OD:600"

fig,axess = subplots(
		len(my_plate.rows), len(my_plate.cols),
		figsize=(15,10),
		sharex="all", sharey="all"
	)

for axess_row,row in zip(axess,my_plate.rows):
	for axes,col in zip(axess_row,my_plate.cols):
		axes.plot(
				my_plate.times[channel]/3600,
				my_plate[row,col]-baseline,
			)

axes.set_yscale("log")
axes.set_xlim( 0,10 )
axes.set_ylim(1e-3,2)


for axes,col in zip(axess[-1],my_plate.cols):
	axes.set_xlabel("hours")
for axes,row in zip(axess[:,0],my_plate.rows):
	axes.set_ylabel(channel)


# Subplot labelling thanks to https://stackoverflow.com/a/25814386/2127008
pad = 20

for axes,col in zip(axess[0],my_plate.cols):
	axes.annotate(
			col,
			xy=(0.5,1), xycoords='axes fraction',
			xytext=(0,pad), textcoords='offset points',
			size='xx-large', ha='center', va='baseline'
		)

for axes,row in zip(axess[:,0],my_plate.rows):
	axes.annotate(
			row,
			xy=(0,0.5), xycoords=axes.yaxis.label,
			xytext=(-axes.yaxis.labelpad-pad,0), textcoords='offset points',
			size='xx-large', ha='center', va='center'
		)

fig.savefig("explicit_plot.pdf",bbox_inches="tight")


