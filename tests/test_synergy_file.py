from synergy_file_reader import SynergyFile
from pytest import mark
from os import path

@mark.parametrize("filename",["columnwise_table.txt"])
def test_time_series(filename):
	data = SynergyFile(path.join("time_series",filename))
	assert len(data)==1
	read = data[0]
	
	assert read.metadata["Software Version"] == (3,2,1)
	assert read.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert read.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert read.metadata["Plate Number"] == "Plate 1"
	assert read.metadata["Reader Type"] == "Synergy H1"
	assert read.metadata["Reading Type"] == "Reader"
	assert read.metadata["procedure"] == "foo\nbar\nquz"


