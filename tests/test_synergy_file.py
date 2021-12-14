from synergy_file_reader import SynergyFile, IGNORED_CHANNELS
from datetime import datetime
from pytest import mark
from os import path
import numpy as np

pytestmark = mark.filterwarnings(
		"ignore:.*will be ignored and not parsed",
	)

@mark.parametrize(
		  "filename,       temperature_ts",
	[
		( "column_matrix.txt", True  ),
		( "column_row.txt"   , True  ),
		( "column_column.txt", True  ),
		( "matrix_matrix.txt", False ),
		( "row_matrix.txt"   , True  ),
	])
def test_time_series(filename,temperature_ts):
	data = SynergyFile(path.join("time_series",filename))
	assert len(data)==1
	plate = data[0]
	
	assert plate.metadata["Software Version"] == (3,2,1)
	assert plate.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert plate.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert plate.metadata["Plate Number"] == "Plate 1"
	assert plate.metadata["Reader Type"] == "Synergy H1"
	assert plate.metadata["Reader Serial Number"] == "18092726"
	assert plate.metadata["Reading Type"] == "Reader"
	assert plate.metadata["procedure"] == "foo\nbar\nquz"
	
	assert plate.metadata["datetime"] == datetime(2020,7,23,17,40,7)
	
	assert plate.channels == ["OD:600"]
	assert plate.rows == list("ABCDEFGH")
	assert plate.cols == list(range(1,13))
	
	times = plate.times["OD:600"]
	assert times[0] == 9*60+10
	assert times[-1] == 17*3600+29*60+10
	assert np.all( np.diff(times)==10*60 )
	
	if temperature_ts:
		temps = plate.temperatures["OD:600"]
		assert len(times) == len(temps)
		assert temps[ 0] == 30.0
		assert temps[-1] == 30.1
		assert temps[ 5] == 30.1
		assert plate.temperature_range == (30.0,30.1)
	else:
		assert plate.temperature_range == ( 0.0,30.1)
	
	assert plate["C12" ,"OD:600"][2] == 0.088
	assert plate["C",12,"OD:600"][2] == 0.088
	assert plate["C",12         ][2] == 0.088
	assert plate["C12"          ][2] == 0.088
	assert plate["c12" ,"OD:600"][2] == 0.088
	
	assert plate["A1" ][ 0] == 0.093
	assert plate["H12"][-1] == 0.099
	
	assert plate.results["Max V"]["D",2,"OD:600"] == -0.060
	assert plate.results["t at Max V"]["H11","OD:600"] == 5050
	assert plate.results["t at Max V"]["H11"] == 5050


@mark.parametrize(
		  "filename,     temperature_ts, separator",
	[
		( "column.txt"   ,   True ,       "\t" ),
		( "rowwise.txt"  ,   True ,       "\t" ),
		( "matrix.txt"   ,   False,       "\t" ),
		( "semicolon.txt",   True ,       ";"  ),
	])
def test_multiple_observables(filename,temperature_ts,separator):
	data = SynergyFile(
			path.join("multiple_observables",filename),
			separator
		)
	assert len(data)==1
	plate = data[0]
	
	assert plate.metadata["Software Version"] == (3,2,1)
	assert plate.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert plate.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert plate.metadata["Plate Number"] == "Plate 1"
	assert plate.metadata["Reader Type"] == "Synergy H1"
	assert plate.metadata["Reader Serial Number"] == "18092726"
	assert plate.metadata["Reading Type"] == "Reader"
	assert plate.metadata["procedure"] == "foo\tbar\nquz"
	
	assert plate.metadata["datetime"] == datetime(2020,7,24,15,27,56)
	
	assert plate.channels == ["OD:600","485,528","530,580"]
	assert plate.rows == list("ABCDEFGH")
	assert plate.cols == list(range(1,13))
	
	for channel,offset in [ ("OD:600",108), ("485,528",159), ("530,580",228) ]:
		times = plate.times[channel]
		assert times[0] == offset
		assert times[-1] == offset+20*60
		assert np.all( np.diff(times)==5*60 )
	
	if temperature_ts:
		for channel in plate.channels:
			temps = plate.temperatures[channel]
			assert len(plate.times[channel]) == len(temps)
			assert all( temp==30.0 for temp in temps )
	assert plate.temperature_range == (30.0,30.0)
	
	assert plate["B12" ,"485,528"][2] == 48
	assert plate["B",12,"485,528"][2] == 48
	
	assert plate["H",12,"530,580"][4] == 28
	assert plate["C",2,"OD:600"][4] == 0.085

@mark.parametrize(
		"filename",
	[
		"matrix.txt",
		"matrix_grouped.txt",
		"row.txt",
		"row_grouped.txt",
		"column.txt",
		"column_grouped.txt",
	])
def test_time_series(filename):
	data = SynergyFile(path.join("single_measurement",filename))
	assert len(data)==1
	plate = data[0]
	
	assert plate.metadata["Software Version"] == (3,2,1)
	assert plate.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert plate.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert plate.metadata["Plate Number"] == "Plate 1"
	assert plate.metadata["Reader Type"] == "Synergy H1"
	assert plate.metadata["Reader Serial Number"] == "18092726"
	assert plate.metadata["Reading Type"] == "Reader"
	assert plate.metadata["procedure"] == "foo\nbar\nquz"
	
	assert plate.temperature_range == (30.0,30.1)
	
	assert plate.metadata["datetime"] == datetime(2020,7,24,15,55,48)
	
	assert plate.channels == ["Abs:600","Abs:700","Fluo:485,528"]
	assert plate.rows == list("ABCDEFGH")
	assert plate.cols == list(range(1,13))
	
	assert plate["B5","Abs:600"] == 0.101
	assert plate["D6","Abs:700"] == 0.097
	assert plate["G11","Fluo:485,528"] == 104

def test_multiple_with_gain():
	data = SynergyFile("multiple_with_gain.txt")
	assert len(data)==2
	
	for plate in data:
		assert plate.metadata["Software Version"] == (3,3,14)
		assert plate.metadata["Experiment File Path"] == r"C:\foo.xpt"
		assert plate.metadata["Protocol File Path"] == r"C:\bar.prt"
		assert plate.metadata["Plate Number"] == "Plate 1"
		assert plate.metadata["Reader Type"] == "Synergy H1"
		assert plate.metadata["Reader Serial Number"] == "14112519"
		assert plate.metadata["Reading Type"] == "Reader"
		assert plate.rows == list("ABCDEFGH")
		assert plate.cols == list(range(1,13))
	
	assert data[0].metadata["procedure"] == "foo\nbar\nquz"
	assert data[1].metadata["procedure"] == "foo\tbar\nquz"
	
	assert data[0].temperature_range == (23.8,23.8)
	assert data[1].temperature_range == (23.9,23.9)
	
	assert data[0].metadata["datetime"] == datetime(2019,12,8,16,22,44)
	assert data[1].metadata["datetime"] == datetime(2019,12,8,16,31,10)
	
	assert data[0].channels == ["YFP:485,530","CFP:360/40,460/40"]
	assert data[1].channels == ["YFP:485,530","CFP:425,475"]
	
	assert data[0].gains == {}
	assert data[1].gains["YFP:485,530"] == 134
	assert data[1].gains["CFP:425,475"] ==  74

	assert data[0]["G3","YFP:485,530"] == 553
	assert data[1]["G3","CFP:425,475"] == 1566
	assert np.isnan( data[1]["G11","YFP:485,530"] )

def test_different_format():
	plate = SynergyFile("different_format.txt")[0]
	
	assert plate.metadata["Software Version"] == (3,3,14)
	assert plate.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert plate.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert plate.metadata["Plate Number"] == "Plate 1"
	assert plate.metadata["Reader Type"] == "Synergy H1"
	assert plate.metadata["Reader Serial Number"] == "14112519"
	assert plate.metadata["Reading Type"] == "Reader"
	assert plate.metadata["procedure"] == "foo\nbar\nquz"
	
	assert plate.metadata["datetime"] == datetime(2020,8,26,15,26,39)
	
	channel = "OD:600"
	assert plate.channels == [channel]
	assert plate.rows == list("ABCDEFGH")
	assert plate.cols == list(range(1,13))
	
	times = plate.times[channel]
	assert times[0] == 550
	assert np.all( np.diff(times)==10*60 )
	
	assert plate.temperatures[channel][0] == 30.0
	assert plate.temperatures[channel][90] == 30.2
	
	assert plate["A1",channel][  0] == 0.091
	assert plate["D7",channel][126] == 1.442

def test_decomposed_results():
	plate = SynergyFile("decomposed_results.txt")[0]
	
	assert plate.metadata["Software Version"] == (3,3,14)
	assert plate.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert plate.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert plate.metadata["Plate Number"] == "Plate 1"
	assert plate.metadata["Reader Type"] == "Synergy H1"
	assert plate.metadata["Reader Serial Number"] == "14112519"
	assert plate.metadata["Reading Type"] == "Reader"
	assert plate.metadata["procedure"] == "foo\nbar\nquz"
	
	assert plate.metadata["datetime"] == datetime(2020,9,22,14,28,31)
	
	channel = "600"
	assert plate.channels == [channel]
	assert plate.rows == list("ABCDEFGH")
	assert plate.cols == list(range(1,13))
	
	times = plate.times[channel]
	assert times[0] == 550
	assert np.all( np.diff(times)==10*60 )
	
	assert plate.temperatures[channel][0] == 30.0
	assert plate.temperatures[channel][160] == 30.2
	
	assert plate["A1" ,channel][ 0] == 0.091
	assert plate["E10",channel][46] == 0.666
	
	assert plate.results["Max V"]["A",1,"600"] == 0.060
	assert plate.results["Lagtime"]["G7","600"] == 13094
	assert plate.results["Lagtime"]["G7"] == 13094
	
	assert np.isnan( plate.results["Lagtime"]["E5"] )

@mark.parametrize( "filename", ["matrix.txt","colwise.txt","rowwise.txt"] )
def test_sample_types(filename):
	plate = SynergyFile(path.join("sample_types",filename))[0]
	
	assert plate.metadata["Software Version"] == (3,3,14)
	assert plate.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert plate.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert plate.metadata["Plate Number"] == "Plate 1"
	assert plate.metadata["Reader Type"] == "Synergy H1"
	assert plate.metadata["Reader Serial Number"] == "14112519"
	assert plate.metadata["Reading Type"] == "Reader"
	assert plate.metadata["procedure"] == "foo\nbar\nquz"
	
	assert plate.metadata["datetime"] == datetime(2021,11,4,15,40,18)
	
	channel = "OD:600"
	assert channel in plate.channels
	assert plate.rows == list("ABCDEFGH")
	assert plate.cols == list(range(1,13))
	
	for row,col,label in [
			("A", 1,  "BLK"     ),
			("H", 2,  "CTL2"    ),
			("B", 2, ("STD1" ,1)),
			("C", 9,  "SPL8"    ),
			("F", 2, ("STDD1",4)),
			("F", 9,  "SPLC11"  ),
		]:
		assert plate.layout[row,col] == label
		assert plate.layout[f"{row}{col}"] == label
		
		label_values = plate[label,channel]
		channel_value = plate[row,col,channel]
		try:
			len(label_values[0])
		except TypeError:
			assert np.any( label_values == channel_value )
		else:
			assert np.any(
					np.all( label_value == channel_value )
					for label_value in label_values
				)
	
	times = plate.times[channel]
	assert times[0] == 2
	assert np.all( np.diff(times)==60 )
	
	assert plate.temperatures[channel][0] == 21.8
	
	assert plate["A1"   ,channel][0] == 0.500
	assert plate["E10"  ,channel][2] == 0.050
	assert plate["SPLC3",channel][2] == 0.050

@mark.parametrize( "filename", ["matrix_noconc.txt","colwise_noconc.txt","rowwise_noconc.txt"] )
def test_sample_types_noconc(filename):
	plate = SynergyFile(path.join("sample_types",filename))[0]
	
	assert plate.metadata["Software Version"] == (3,3,14)
	assert plate.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert plate.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert plate.metadata["Plate Number"] == "Plate 2"
	assert plate.metadata["Reader Type"] == "Synergy H1"
	assert plate.metadata["Reader Serial Number"] == "14112519"
	assert plate.metadata["Reading Type"] == "Reader"
	assert plate.metadata["procedure"] == "foo\nbar\nquz"
	
	assert plate.metadata["datetime"] == datetime(2021,11,8,15,21,55)
	
	channel = "OD:600"
	assert channel in plate.channels
	assert IGNORED_CHANNELS.isdisjoint(plate.channels)
	assert plate.rows == list("ABCDEFGH")
	assert plate.cols == list(range(1,13))
	
	for row,col,label in [
			("A",  1,  "BFR"    ),
			("C",  6,  "CTL1"   ),
			("E",  4,  "XYZ7"   ),
			("H", 12,  "SPLC22" ),
		]:
		assert plate.layout[row,col] == label
		assert plate.layout[f"{row}{col}"] == label
		
		label_values = plate[label,channel]
		channel_value = plate[row,col,channel]
		try:
			len(label_values[0])
		except TypeError:
			assert np.any( label_values == channel_value )
		else:
			assert np.any(
					np.all( label_value == channel_value )
					for label_value in label_values
				)
	
	times = plate.times[channel]
	assert times[0] == 2
	assert np.all( np.diff(times)==60 )
	
	assert plate["A1"    ,channel][0] == 0.096
	assert plate["H12"   ,channel][2] == 0.333
	assert plate["SPLC22",channel][2] == 0.333

@mark.parametrize( "filename", ["single_matrix.txt","single_col.txt","single_row.txt"] )
def test_sample_types_single(filename):
	plate = SynergyFile(path.join("sample_types",filename),verbose=True)[0]
	
	assert plate.metadata["Software Version"] == (3,3,14)
	assert plate.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert plate.metadata["Protocol File Path"] == r""
	assert plate.metadata["Plate Number"] == "Plate 1"
	assert plate.metadata["Reader Type"] == "Synergy H1"
	assert plate.metadata["Reader Serial Number"] == "14112519"
	assert plate.metadata["Reading Type"] == "Reader"
	assert plate.metadata["procedure"] == "foo\nbar\nquz"
	
	assert plate.metadata["datetime"] == datetime(2021,11,16,14,16,33)
	
	channel = "450"
	assert channel in plate.channels
	# assert plate.rows == list("ABCDEFG")
	# assert plate.cols == list(range(1,13))
	
	for row,col,label in [
			("B",  4,   "BLK"       ),
			("E",  3,   "CTL1"      ),
			("F",  7,  ("SPL3",2.5) ),
			("G",  7,  ("SPL3",3.7) ),
		]:
		assert plate.layout[row,col] == label
		assert plate.layout[f"{row}{col}"] == label
		
		label_values = plate[label,channel]
		channel_value = plate[row,col,channel]
		try:
			len(label_values[0])
		except TypeError:
			print(label_values,channel_value)
			assert np.any( np.array(label_values) == channel_value )
		else:
			assert np.any(
					np.all( label_value == channel_value )
					for label_value in label_values
				)
	
	assert plate["A1" ,channel] == 0.102
	assert plate["E3" ,channel] == 1.672
	assert plate["G11",channel] == 0.102

def test_spectrum():
	plate = SynergyFile("spectrum.txt",verbose=True)[0]
	
	assert plate.metadata["Software Version"] == (3,2,1)
	assert plate.metadata["Experiment File Path"] == r"C:\foo.xpt"
	assert plate.metadata["Protocol File Path"] == r"C:\bar.prt"
	assert plate.metadata["Plate Number"] == "Plate 1"
	assert plate.metadata["Reader Type"] == "Synergy H1"
	assert plate.metadata["Reader Serial Number"] == "18092726"
	assert plate.metadata["Reading Type"] == "Reader"
	assert plate.metadata["procedure"] == "foo\nbar\nquz"
	
	assert plate.metadata["datetime"] == datetime(2021,8,24,11,6,35)
	
	channel = "OD_colour"
	assert plate.rows == list("ABCDEFGH")
	assert plate.cols == list(range(1,13))
	
	assert plate["A1" ,(channel,294)] == 0.900
	assert plate["B6" ,(channel,550)] == 0.051
	assert np.isposinf(plate["H12" ,(channel,262)])
	
	assert plate["E9" ,"OD600:600"] == 0.073
	

