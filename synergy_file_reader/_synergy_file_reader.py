from synergy_file_reader.tools import (
		split_well_name, extract_channel,
		parse_number, parse_time, parse_timestamp,
		row_iter,
		LineBuffer,
	)
from math import isnan, inf
from datetime import datetime

format_parsers = [parse_time, parse_number]

class FormatMismatch(Exception): pass
class RepeatingData(Exception): pass

def format_assert(condition):
	if not condition:
		raise FormatMismatch

class ValueError_to_FormatMismatch(object):
	"""
		Context manager that catches all ValueErrors within the context and reraises them as FormatMismatches.
	"""
	def __enter__(self):
		pass
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		if exc_type:
			if issubclass(exc_type,ValueError):
				raise FormatMismatch from exc_value

class Attempt(object):
	def __init__(self,parser,parent):
		self.parser = parser
		self.parent = parent
	
	def __enter__(self):
		return self.parser
	
	def __exit__(self, exc_type, exc_value, exc_traceback):
		if exc_type:
			if issubclass(exc_type,ValueError):
				return True
		else:
			self.parent.success = True

class TryFormats(object):
	def __init__(self):
		self.success = False
	
	def __iter__(self):
		for format_parser in format_parsers:
			yield Attempt(format_parser,self)
			if self.success:
				break
		else:
			raise FormatMismatch

class SynergyResult(object):
	def __init__(self):
		self.data = {}
		self.rows = []
		self.cols = []
		self.channels = []
	
	def _add_row(self,row):
		if row not in self.rows:
			if self.rows:
				assert len(row)>len(self.rows[-1]) or row>self.rows[-1]
			self.rows.append(row)
	
	def _add_col(self,col):
		if col not in self.cols:
			if self.cols:
				assert col > self.cols[-1]
			self.cols.append(col)
	
	def _add_channel(self,channel):
		if channel not in self.channels:
			self.channels.append(channel)
	
	def keys(self):
		return self.data.keys()
	
	def _convert_index(self,index):
		# Avoid string as single index being interpreted as iterable:
		if isinstance(index,str):
			index = [index]
		else:
			index = list(index)
		
		try:
			row,col = split_well_name(index[0])
			del index[0]
		except ValueError:
			row,col = index[:2]
			del index[:2]
		
		row = row.upper()
		
		if len(index)==0:
			if len(self.channels)==1:
				channel = self.channels[0]
			else:
				raise ValueError("You must specify a channel as there is more than one in this read.")
		elif len(index)==1:
			channel = index[0]
		else:
			raise ValueError("Too many indices.")
		
		return row,col,channel

	def __setitem__(self,index,result):
		row,col,channel = self._convert_index(index)
		if (row,col,channel) in self.keys():
			raise RepeatingData
		else:
			self._add_row(row)
			self._add_col(col)
			self._add_channel(channel)
			self.data[row,col,channel] = result
	
	def __getitem__(self,index):
		return self.data[self._convert_index(index)]


class SynergyRead(SynergyResult):
	def __init__(self):
		super().__init__()
		self.metadata = {}
		self.times = None
		self.temperatures = {}
		self.results = {}
		self.gains = {}
	
	def _add_time(self,time,channel):
		if self.times is None:
			self.times = {}
		self._add_channel(channel)
		if channel in self.times:
			if time != self.times[channel][-1]:
				assert time > self.times[channel][-1]
				self.times[channel].append(time)
		else:
			self.times[channel] = [time]
	
	def _add_temperature(self,time,channel,temperature):
		self._add_time(time,channel)
		self._add_channel(channel)
		try:
			self.temperatures[channel].append(temperature)
		except KeyError:
			self.temperatures[channel] = [temperature]
		else:
			assert len(self.temperatures[channel])==len(self.times[channel])
	
	def _add_gain(self,channel,value):
		self._add_channel(channel)
		if channel in self.gains:
			raise ValueError("Duplicate gain value")
		self.gains[channel] = value
	
	def _add_raw_result(self,channel,row,col,value,time=None):
		if time is not None:
			self._add_time(time,channel)
			if (row,col,channel) in self.keys():
				self[row,col,channel].append(value)
				assert len(self[row,col,channel])==len(self.times[channel])
			else:
				self[row,col,channel] = [value]
		else:
			assert self.times is None
			self[row,col,channel] = value
	
	def _add_result(self,name,row,col,value):
		try:
			key,channel = extract_channel(name)
		except ValueError:
			self._add_raw_result(name,row,col,value)
			return
		
		if name not in self.results:
			self.results[name] = SynergyResult()
		self.results[name][row,col,channel] = value
	
	def _add_metadata(self,**new_metadata):
		if "Min Temperature" in new_metadata:
			assert "Max Temperature" in new_metadata
			self._update_temperature_range(
					parse_number(new_metadata.pop("Min Temperature")),
					parse_number(new_metadata.pop("Max Temperature")),
				)
		
		try:
			act_temp = parse_number(new_metadata.pop("Actual Temperature"))
		except KeyError:
			pass
		else:
			self._update_temperature_range(act_temp,act_temp)
		
		# After Min and Max Temperatures as these can indeed repeat:
		if any( key in self.metadata for key in new_metadata ):
			raise RepeatingData
		
		if "Date" in new_metadata:
			assert "Time" in new_metadata
			date_and_time = new_metadata.pop("Date") + " " + new_metadata.pop("Time")
			for datetime_format in [
						"%m/%d/%Y %I:%M:%S %p",
						"%Y-%m-%d %H:%M:%S",
				]:
				try:
					self.metadata["datetime"] = datetime.strptime(
						date_and_time,
						datetime_format,
					)
				except ValueError:
					continue
				else:
					break
			else:
				raise ValueError(f"{date_and_time} does not match any implemented time format.")
		
		for key,value in new_metadata.items():
			if key=="Software Version":
				value = tuple( int(x) for x in value.split(".") )
			
			self.metadata[key] = value
	
	def _update_temperature_range(self,min_temp,max_temp):
		if not hasattr(self,"_temperature_range"):
			self._temperature_range = (inf,-inf)
		self._temperature_range = (
				min(self._temperature_range[0],min_temp),
				max(self._temperature_range[1],max_temp),
			)

	@property
	def temperature_range(self):
		if hasattr(self,"_temperature_range"):
			return self._temperature_range
		else:
			all_temps = [
					temp
					for temps in self.temperatures.values()
					for temp in temps
				]
			return min(all_temps),max(all_temps)
	
	# def __repr__(self):
	# 	return(f"SynergyRead( {self.metadata}, {self.times}, {self.temperatures}, {self.raw_data} )")

class SynergyFile(list):
	def __init__(self,filename,separator="\t",encoding="iso-8859-1"):
		super().__init__()
		self.sep = separator
		self._new_read()
		
		with open(filename,"r",encoding=encoding) as f:
			self._line_buffer = LineBuffer(f.read().splitlines())
		
		self._parse_file()
	
	def _parse_file(self):
		while self._line_buffer:
			for parser in (
					self._parse_raw_data_matrix,
					self._parse_raw_data_row,
					self._parse_raw_data_column,
					self._parse_results_matrix,
					self._parse_results_row,
					self._parse_results_column,
					self._parse_single_matrix,
					self._parse_single_row,
					self._parse_single_column,
					self._parse_procedure,
					self._parse_gain_values,
					self._parse_metadata,
				):
				try:
					parser()
				except FormatMismatch:
					continue
				except RepeatingData:
					self._new_read()
					break
				else:
					break
			else:
				raise ValueError("File does not appear to have a valid or implemented format.")
	
	def _new_read(self):
		self.append(SynergyRead())
	
	def _parse_metadata(self):
		new_metadata = {}
		
		with self._line_buffer as line_iter:
			# looping over lines here (instead doing one at a time) to:
			# • get time and date together
			# • raise RepeatingData as early as possible
			
			for line in line_iter:
				if line == "":
					break
				
				format_assert( line.count(self.sep) == 1 )
				key,_,value = line.partition(self.sep)
				if key.endswith(":"):
					key = key[:-1]
				new_metadata[key] = value
			
			self[-1]._add_metadata(**new_metadata)
	
	def _parse_procedure(self):
		with self._line_buffer as line_iter:
			format_assert( next(line_iter) == "Procedure Details" )
			format_assert( next(line_iter) == "" )
			
			procedure = []
			while line:=next(line_iter):
				procedure.append(line.replace(self.sep,"\t"))
			self[-1]._add_metadata( procedure = "\n".join(procedure) )
	
	def _parse_gain_values(self):
		with self._line_buffer as line_iter:
			format_assert( next(line_iter) == "Automatic gain values\t " )
			gains = []
			for line in line_iter:
				if line=="": break
				label,value = line.split(self.sep)
				Gain,_,channel = label.partition("(")
				format_assert( Gain == "Gain" )
				format_assert( channel.endswith(")") )
				channel = channel[:-1]
				with ValueError_to_FormatMismatch():
					value = float(value)
				gains.append((channel,value))
			
			for channel,value in gains:
				self[-1]._add_gain(channel,value)
	
	def _parse_results_matrix(self):
		with self._line_buffer as line_iter:
			format_assert( next(line_iter) == "Results" )
			
			with ValueError_to_FormatMismatch():
				empty,*cols = next(line_iter).split(self.sep)
				cols = [ int(col) for col in cols ]
			format_assert( cols == list(range(1,len(cols)+1)) )
			format_assert( empty == "" )
			
			results = []
			row = None
			expected_rows = row_iter()
			for line in line_iter:
				if line=="": break
				new_row,*numbers,name = line.split(self.sep)
				
				if new_row:
					format_assert( new_row == next(expected_rows) )
					row = new_row
				format_assert( row is not None )
				
				for attempt in TryFormats():
					with attempt as format_parser:
						numbers = [ format_parser(number) for number in numbers ]
				
				results.append((row,numbers,name))
			
			for row,numbers,name in results:
				for col,number in zip(cols,numbers):
					self[-1]._add_result(name,row,col,number)
	
	def _parse_results_row(self):
		with self._line_buffer as line_iter:
			format_assert( next(line_iter) == "Results" )
			format_assert( next(line_iter) == "" )
			
			with ValueError_to_FormatMismatch():
				Well,*names = next(line_iter).split(self.sep)
			format_assert( Well=="Well" )
			
			results = []
			for line in line_iter:
				if line=="": break
				
				well,*numbers = line.split(self.sep)
				with ValueError_to_FormatMismatch():
					row,col = split_well_name(well)
				
				format_assert( len(names)==len(numbers) )
				for name,number in zip(names,numbers):
					for attempt in TryFormats():
						with attempt as format_parser:
							number = format_parser(number)
					results.append((name,row,col,number))
			
			for name,row,col,number in results:
				self[-1]._add_result(name,row,col,number)
	
	def _parse_results_column(self):
		with self._line_buffer as line_iter:
			format_assert( next(line_iter) == "Results" )
			format_assert( next(line_iter) == "" )
			
			with ValueError_to_FormatMismatch():
				Well,*wells,last = next(line_iter).split(self.sep)
				wells = [ split_well_name(well) for well in wells ]
			format_assert( Well == "Well" )
			format_assert( last == "" )
			
			results = []
			for line in line_iter:
				if line=="": break
				name,*numbers,last = line.split(self.sep)
				format_assert( len(wells) == len(numbers) )
				format_assert( last == "" )
				
				for attempt in TryFormats():
					with attempt as format_parser:
						numbers = [ format_parser(number) for number in numbers ]
				
				results.append((name,numbers))
			
			for name,numbers in results:
				for (row,col),number in zip(wells,numbers):
					self[-1]._add_result(name,row,col,number)
	
	def _parse_raw_data_column(self):
		with self._line_buffer as line_iter:
			channel = next(line_iter)
			format_assert( self.sep not in channel )
			format_assert( next(line_iter) == "" )
			
			with ValueError_to_FormatMismatch():
				Time,Temp,*wells = next(line_iter).split(self.sep)
			format_assert( Time == "Time" )
			format_assert( Temp == "T° "+channel )
			
			results = []
			while line:=next(line_iter):
				with ValueError_to_FormatMismatch():
					time,temperature,*numbers = line.split(self.sep)
					numbers = [ parse_number(number) for number in numbers ]
					time = parse_time(time)
					temperature = parse_number(temperature)
				format_assert( len(numbers) == len(wells) )
				results.append((time,temperature,numbers))
			
			for time,temperature,numbers in results:
				if time==0 and all(isnan(number) for number in numbers):
					continue
				self[-1]._add_temperature(time,channel,temperature)
				for well,number in zip(wells,numbers):
					self[-1]._add_raw_result(channel,*split_well_name(well),number,time)
	
	def _parse_raw_data_row(self):
		with self._line_buffer as line_iter:
			channel = next(line_iter)
			format_assert( self.sep not in channel )
			format_assert( next(line_iter) == "" )
			
			with ValueError_to_FormatMismatch():
				label,*times,last = next(line_iter).split(self.sep)
			format_assert( last == "" )
			format_assert( label == "Time" )
			with ValueError_to_FormatMismatch():
				times = [ parse_time(time) for time in times ]
				label,*temperatures,last = next(line_iter).split(self.sep)
			format_assert( last == "" )
			format_assert( label == "T° "+channel )
			format_assert( len(temperatures) == len(times) )
			with ValueError_to_FormatMismatch():
				temperatures = [ float(temperature) for temperature in temperatures ]
			
			results = []
			wells = []
			for line in line_iter:
				if line=="": break
				with ValueError_to_FormatMismatch():
					well,*numbers,last = line.split(self.sep)
					numbers = [ parse_number(number) for number in numbers ]
				format_assert( last == "" )
				format_assert( len(numbers) == len(times) )
				wells.append(well)
				results.append(numbers)
			
			for i,(time,temperature,*numbers) in enumerate(zip(times,temperatures,*results)):
				if i>0 and time==0:
					break
				self[-1]._add_temperature(time,channel,temperature)
				for well,number in zip(wells,numbers):
					self[-1]._add_raw_result(channel,*split_well_name(well),number,time)
	
	def _parse_raw_data_matrix(self):
		with self._line_buffer as line_iter:
			channel, _, timestamp = next(line_iter).partition(" - ")
			with ValueError_to_FormatMismatch():
				number,time = parse_timestamp(timestamp)
				format_assert( (number,time) == parse_timestamp(next(line_iter)) )
				empty,*cols = next(line_iter).split(self.sep)
				format_assert( empty == "" )
				cols = [ int(col) for col in cols ]
			format_assert( cols==list(range(1,len(cols)+1)) )
			format_assert( cols )
			
			results = []
			for line,expected_row in zip(line_iter,row_iter()):
				if line=="": break
				row,*numbers,label = line.split(self.sep)
				format_assert( len(numbers) == len(cols) )
				format_assert( row == expected_row )
				format_assert( label == f"{channel} Read#{number}" )
				with ValueError_to_FormatMismatch():
					numbers = [ parse_number(number) for number in numbers ]
				results.append((row,numbers))
			
			if time==0 and number>0:
				for _,numbers in results:
					format_assert( all(isnan(number) for number in numbers) )
			else:
				for row,numbers in results:
					for col,number in zip(cols,numbers):
						self[-1]._add_raw_result(channel,row,col,number,time)

	def _parse_single_matrix(self):
		with self._line_buffer as line_iter:
			channel = next(line_iter)
			format_assert( self.sep not in channel )
			
			with ValueError_to_FormatMismatch():
				empty,*cols = next(line_iter).split(self.sep)
				cols = [ int(col) for col in cols ]
			format_assert( empty == "" )
			format_assert( cols )
			format_assert( cols==list(range(1,len(cols)+1)) )
			
			results = []
			for line,expected_row in zip(line_iter,row_iter()):
				if line=="": break
				with ValueError_to_FormatMismatch():
					row,*numbers,label = line.split(self.sep)
				format_assert( label == channel )
				format_assert( row == expected_row )
				
				with ValueError_to_FormatMismatch():
					numbers = [ parse_number(number) for number in numbers ]
				
				results.append((row,numbers))
			
			for row,numbers in results:
				for col,number in zip(cols,numbers):
					self[-1]._add_raw_result(channel,row,col,number)
	
	def _parse_single_row(self):
		with self._line_buffer as line_iter:
			channel = next(line_iter)
			format_assert( self.sep not in channel )
			format_assert( next(line_iter) == "" )
			format_assert( next(line_iter) == "Well"+self.sep+channel )
			
			results = []
			for line in line_iter:
				if line=="": break
				well,number = line.split(self.sep)
				with ValueError_to_FormatMismatch():
					number = parse_number(number)
					row,col = split_well_name(well)
				results.append((row,col,number))
			
			for row,col,number in results:
				self[-1]._add_raw_result(channel,row,col,number)
	
	def _parse_single_column(self):
		with self._line_buffer as line_iter:
			channel = next(line_iter)
			format_assert( self.sep not in channel )
			format_assert( next(line_iter) == "" )
			
			with ValueError_to_FormatMismatch():
				Well,*wells,last = next(line_iter).split(self.sep)
				wells = [ split_well_name(well) for well in wells ]
			format_assert( Well == "Well" )
			format_assert( last == "" )
			
			channel_2,*numbers,last = next(line_iter).split(self.sep)
			format_assert( last == "" )
			format_assert( channel_2 == channel )
			with ValueError_to_FormatMismatch():
				numbers = [ parse_number(number) for number in numbers ]
			
			format_assert( next(line_iter) == "" )
			
			for (row,col),number in zip(wells,numbers):
				self[-1]._add_raw_result(channel,row,col,number)


