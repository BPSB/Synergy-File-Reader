from synergy_file_reader import SynergyFile
from os import path

def test_plot():
	plate = SynergyFile(path.join("time_series","row_matrix.txt"))[0]
	fig,axess = plate.plot()
	fig.savefig("plot.pdf")
