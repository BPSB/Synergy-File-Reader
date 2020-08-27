from synergy_file_reader import SynergyFile
from datetime import datetime
from pytest import mark
from os import path
import numpy as np

@mark.parametrize(
		  "filename,                         temperature_ts",
	[
		( "columnwise_table_matrix.txt"          , True  ),
		( "columnwise_table_rowwise_table.txt"   , True  ),
		( "columnwise_table_columnwise_table.txt", True  ),
		( "matrix_matrix.txt"                    , False ),
		( "rowwise_table_matrix.txt"             , True  ),
	])
def test_time_series(filename,temperature_ts):
	data = SynergyFile(path.join("time_series",filename))
	assert len(data)==1
	read = data[0]
	
	assert read.metadata["Software Version"] == (3,2,1)
	assert read.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert read.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert read.metadata["Plate Number"] == "Plate 1"
	assert read.metadata["Reader Type"] == "Synergy H1"
	assert read.metadata["Reader Serial Number"] == "18092726"
	assert read.metadata["Reading Type"] == "Reader"
	assert read.metadata["procedure"] == "foo\nbar\nquz"
	
	assert read.metadata["datetime"] == datetime(2020,7,23,17,40,7)
	
	assert read.channels == ["OD:600"]
	assert read.rows == list("ABCDEFGH")
	assert read.cols == list(range(1,13))
	
	times = read.times["OD:600"]
	assert times[0] == 9*60+10
	assert times[-1] == 17*3600+29*60+10
	assert np.all( np.diff(times)==10*60 )
	
	if temperature_ts:
		temps = read.temperatures["OD:600"]
		assert len(times) == len(temps)
		assert temps[ 0] == 30.0
		assert temps[-1] == 30.1
		assert temps[ 5] == 30.1
		assert read.temperature_range == (30.0,30.1)
	else:
		assert read.temperature_range == ( 0.0,30.1)
	
	assert read["C12" ,"OD:600"][2] == 0.088
	assert read["C",12,"OD:600"][2] == 0.088
	assert read["C",12         ][2] == 0.088
	assert read["C12"          ][2] == 0.088
	assert read["c12" ,"OD:600"][2] == 0.088
	
	assert read["A1" ][ 0] == 0.093
	assert read["H12"][-1] == 0.099
	
	assert read.results["Max V"]["D",2,"OD:600"] == -0.060
	assert read.results["t at Max V"]["H11","OD:600"] == 5050
	assert read.results["t at Max V"]["H11"] == 5050


@mark.parametrize(
		  "filename,                         temperature_ts",
	[
		( "column.txt"          , True  ),
		( "matrix.txt"          , False ),
	])
def test_multiple_observables(filename,temperature_ts):
	data = SynergyFile(path.join("multiple_observables",filename))
	assert len(data)==1
	read = data[0]
	
	assert read.metadata["Software Version"] == (3,2,1)
	assert read.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert read.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert read.metadata["Plate Number"] == "Plate 1"
	assert read.metadata["Reader Type"] == "Synergy H1"
	assert read.metadata["Reader Serial Number"] == "18092726"
	assert read.metadata["Reading Type"] == "Reader"
	assert read.metadata["procedure"] == "foo\nbar\nquz"
	
	assert read.metadata["datetime"] == datetime(2020,7,24,15,27,56)
	
	assert read.channels == ["OD:600","485,528","530,580"]
	assert read.rows == list("ABCDEFGH")
	assert read.cols == list(range(1,13))
	
	for channel,offset in [ ("OD:600",108), ("485,528",159), ("530,580",228) ]:
		times = read.times[channel]
		assert times[0] == offset
		assert times[-1] == offset+20*60
		assert np.all( np.diff(times)==5*60 )
	
	if temperature_ts:
		for channel in read.channels:
			temps = read.temperatures[channel]
			assert len(read.times[channel]) == len(temps)
			assert all( temp==30.0 for temp in temps)
	assert read.temperature_range == (30.0,30.0)
	
	assert read["B12" ,"485,528"][2] == 48
	assert read["B",12,"485,528"][2] == 48
	assert read["b12" ,"485,528"][2] == 48
	
	assert read["H",12,"530,580"][4] == 28
	assert read["C",2,"OD:600"][4] == 0.085

