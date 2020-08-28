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
		self.results = []
	
	def add_row(self,row):
		if row not in self.rows:
			if self.rows:
				assert len(row)>len(self.rows[-1]) or row>self.rows[-1]
			self.rows.append(row)
	
	def add_col(self,col):
		if col not in self.cols:
			if self.cols:
				assert col > self.cols[-1]
			self.cols.append(col)
	
	def add_channel(self,channel):
		if channel not in self.channels:
			self.channels.append(channel)
	
	def keys(self):
		return self.data.keys()
	
	def convert_index(self,index):
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
		row,col,channel = self.convert_index(index)
		self.add_row(row)
		self.add_col(col)
		self.add_channel(channel)
		if (row,col,channel) in self.keys():
			raise RepeatingData
		else:
			self.data[row,col,channel] = result
	
	def __getitem__(self,index):
		return self.data[self.convert_index(index)]


class SynergyRead(SynergyResult):
	def __init__(self):
		super().__init__()
		self.metadata = {}
		self.times = {}
		self.temperatures = {}
		self.results = {}
	
	def add_time(self,time,channel):
		self.add_channel(channel)
		if channel in self.times:
			if time != self.times[channel][-1]:
				assert time > self.times[channel][-1]
				self.times[channel].append(time)
		else:
			self.times[channel] = [time]
	
	def add_temperature(self,time,channel,temperature):
		self.add_time(time,channel)
		self.add_channel(channel)
		try:
			self.temperatures[channel].append(temperature)
		except KeyError:
			self.temperatures[channel] = [temperature]
		else:
			assert len(self.temperatures[channel])==len(self.times[channel])
	
	def add_raw_result(self,time,channel,row,col,value):
		self.add_time(time,channel)
		if (row,col,channel) in self.keys():
			self[row,col,channel].append(value)
			assert len(self[row,col,channel])==len(self.times[channel])
		else:
			self[row,col,channel] = [value]
	
	def add_result(self,name,channel,row,col,value):
		if name not in self.results:
			self.results[name] = SynergyResult()
		
		self.results[name][row,col,channel] = value
	
	def add_metadata(self,**new_metadata):
		if "Min Temperature" in new_metadata:
			assert "Max Temperature" in new_metadata
			self.update_temperature_range(
					parse_number(new_metadata.pop("Min Temperature")),
					parse_number(new_metadata.pop("Max Temperature")),
				)
		
		# After Min and Max Temperatures as these can indeed repeat:
		if any( key in self.metadata for key in new_metadata ):
			raise RepeatingData
		
		if "Date" in new_metadata:
			assert "Time" in new_metadata
			self.metadata["datetime"] = datetime.strptime(
				new_metadata.pop("Date") + " " + new_metadata.pop("Time"),
				"%m/%d/%Y %I:%M:%S %p"
			)
		
		for key,value in new_metadata.items():
			if key=="Software Version":
				value = tuple( int(x) for x in value.split(".") )
			
			self.metadata[key] = value
	
	def update_temperature_range(self,min_temp,max_temp):
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
		self.new_read()
		
		with open(filename,"r",encoding=encoding) as f:
			self.line_buffer = LineBuffer(f.read().splitlines())
		
		self.parse_file()
	
	def parse_file(self):
		while self.line_buffer:
			for parser in (
					self.parse_raw_data_matrix,
					self.parse_raw_data_rowwise_table,
					self.parse_raw_data_columnwise_table,
					self.parse_results_matrix,
					self.parse_results_rowwise_table,
					self.parse_results_columnwise_table,
					self.parse_procedure,
					self.parse_metadata,
				):
				try:
					parser()
				except FormatMismatch:
					continue
				except RepeatingData:
					self.new_read()
					break
				else:
					break
			else:
				raise ValueError("File does not appear to have a valid or implemented format.")
	
	def new_read(self):
		self.append(SynergyRead())
	
	def parse_metadata(self):
		new_metadata = {}
		
		with self.line_buffer as line_iter:
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
		
		self[-1].add_metadata(**new_metadata)
	
	def parse_procedure(self):
		with self.line_buffer as line_iter:
			format_assert( next(line_iter) == "Procedure Details" )
			format_assert( next(line_iter) == "" )
			
			procedure = []
			while line:=next(line_iter):
				procedure.append(line)
			self[-1].add_metadata( procedure = "\n".join(procedure) )
	
	def parse_gain_values(self):
		# TODO
		pass
	
	def parse_results_matrix(self):
		with self.line_buffer as line_iter:
			format_assert(next(line_iter)=="Results")
			
			with ValueError_to_FormatMismatch():
				cols = [int(c) for c in next(line_iter).split(self.sep)[1:]]
			format_assert( cols==list(range(1,len(cols)+1)) )
			
			results = []
			row = None
			for line in line_iter:
				if line=="":
					break
				new_row,*numbers,name = line.split(self.sep)
				
				if new_row:
					format_assert(new_row.isupper())
					format_assert(new_row.isalpha())
					row = new_row
				format_assert(row is not None)
				
				for attempt in TryFormats():
					with attempt as format_parser:
						numbers = [format_parser(number) for number in numbers]
				
				results.append((row,numbers,*extract_channel(name)))
			
			for row,numbers,key,channel in results:
				for col,number in zip(cols,numbers):
					self[-1].add_result(key,channel,row,col,number)
	
	def parse_results_rowwise_table(self):
		with self.line_buffer as line_iter:
			format_assert( next(line_iter)=="Results" )
			format_assert( next(line_iter)=="" )
			
			cols = next(line_iter).split(self.sep)
			format_assert( cols[0]=="Well" )
			
			with ValueError_to_FormatMismatch():
				fields = [ extract_channel(col) for col in cols[1:] ]
			
			results = []
			for line in line_iter:
				if line=="":
					break
				well,*numbers = line.split(self.sep)
				
				with ValueError_to_FormatMismatch():
					row,col = split_well_name(well)
				
				format_assert( len(fields)==len(numbers) )
				
				for (key,channel),number in zip(fields,numbers):
					for attempt in TryFormats():
						with attempt as format_parser:
							number = format_parser(number)
					
					results.append((row,col,number,key,channel))
			
			for row,col,number,key,channel in results:
				self[-1].add_result(key,channel,row,col,number)
	
	def parse_results_columnwise_table(self):
		with self.line_buffer as line_iter:
			format_assert( next(line_iter)=="Results" )
			format_assert( next(line_iter)=="" )
			
			cols = next(line_iter).rstrip(self.sep).split(self.sep)
			format_assert( cols[0]=="Well" )
			
			with ValueError_to_FormatMismatch():
				wells = [ split_well_name(col) for col in cols[1:] ]
			
			results = []
			for line in line_iter:
				if line=="":
					break
				name,*numbers = line.rstrip(self.sep).split(self.sep)
				
				with ValueError_to_FormatMismatch():
					key,channel = extract_channel(name)
				
				format_assert( len(wells)==len(numbers) )
				
				for attempt in TryFormats():
					with attempt as format_parser:
						numbers = [format_parser(number) for number in numbers]
				
				results.append((key,channel,numbers))
			
			for key,channel,numbers in results:
				for (row,col),number in zip(wells,numbers):
					self[-1].add_result(key,channel,row,col,number)
	
	def parse_raw_data_columnwise_table(self):
		with self.line_buffer as line_iter:
			channel = next(line_iter)
			format_assert( self.sep not in channel )
			format_assert( next(line_iter) == "" )
			
			fields = next(line_iter).split(self.sep)
			format_assert( len(fields) >= 3 )
			format_assert( fields[0] == "Time" )
			format_assert( fields[1] == "T° "+channel )
			wells = fields[2:]
			
			results = []
			while line:=next(line_iter):
				time,temperature,*numbers = line.split(self.sep)
				format_assert( len(numbers) == len(wells) )
				with ValueError_to_FormatMismatch():
					result = parse_time(time),parse_number(temperature),*map(parse_number,numbers)
				results.append(result)
		
		for time,temperature,*numbers in results:
			if time==0 and all(isnan(number) for number in numbers):
				continue
			self[-1].add_temperature(time,channel,temperature)
			for well,number in zip(wells,numbers):
				self[-1].add_raw_result(time,channel,*split_well_name(well),number)
	
	def parse_raw_data_rowwise_table(self):
		with self.line_buffer as line_iter:
			channel = next(line_iter)
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
					numbers = list(map(parse_number,numbers))
				format_assert( last == "" )
				format_assert( len(numbers) == len(times) )
				wells.append(well)
				results.append(numbers)
		
		for i,(time,temperature,*numbers) in enumerate(zip(times,temperatures,*results)):
			if i>0 and time==0:
				break
			self[-1].add_temperature(time,channel,temperature)
			for well,number in zip(wells,numbers):
				self[-1].add_raw_result(time,channel,*split_well_name(well),number)
	
	def parse_raw_data_matrix(self):
		with self.line_buffer as line_iter:
			channel, _, timestamp = next(line_iter).partition(" - ")
			with ValueError_to_FormatMismatch():
				number,time = parse_timestamp(timestamp)
				format_assert( (number,time) == parse_timestamp(next(line_iter)) )
				headers = next(line_iter).split(self.sep)
				format_assert( headers[0] == "" )
				cols = [ int(c) for c in headers[1:] ]
			format_assert( cols==list(range(1,len(cols)+1)) )
			
			results = []
			for line,expected_row in zip(line_iter,row_iter()):
				if line == "":
					break
				row,*numbers,label = line.split(self.sep)
				format_assert( len(numbers) == len(cols) )
				format_assert( row == expected_row )
				format_assert( label == f"{channel} Read#{number}" )
				with ValueError_to_FormatMismatch():
					numbers = list(map(parse_number,numbers))
				
				results.append((row,numbers))
		
		if time==0 and number>0:
			for _,numbers in results:
				format_assert( all(isnan(number) for number in numbers) )
		else:
			for row,numbers in results:
				for col,number in zip(cols,numbers):
					self[-1].add_raw_result(time,channel,row,col,number)

