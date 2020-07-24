
def to_seconds(time):
	hours, minutes, seconds = map(int,time.split(":"))
	return (hours*60+minutes)*60+seconds

class FormatMismatch(Exception): pass
class RepeatingData(Exception): pass

class SynergyRead(object):
	def __init__(self):
		self.metadata = {}
		self.raw_data = {}
		self.times = []
		self.temperatures = {}
	
	def add_time(self,time):
		if self.times:
			if time != self.times[-1]:
				assert time>self.times[-1]
				self.times.append(time)
		else:
			self.times.append(time)
	
	def add_temperature(self,time,channel,temperature):
		self.add_time(time)
		try:
			self.temperatures[channel].append(temperature)
		except KeyError:
			self.temperatures[channel] = [temperature]
		else:
			assert len(self.temperatures[channel])==len(self.times)
	
	def add_result(self,time,channel,well,value):
		self.add_time(time)
		try:
			self.raw_data[well,channel].append(value)
		except KeyError:
			self.raw_data[well,channel] = [value]
		else:
			assert len(self.raw_data[well,channel])==len(self.times)
	
	def __repr__(self):
		return(f"SynergyRead( {self.metadata}, {self.times}, {self.temperatures}, {self.raw_data} )")

class LineBuffer(object):
	def __init__(self,lines):
		self.lines = lines
		self.pos = 0
	
	def clear_empty_lines(self):
		while self.lines and self.lines[0]=="":
			self.lines.pop(0)
	
	def __iter__(self):
		self.clear_empty_lines()
		for self.pos,line in enumerate(self.lines):
			yield line
	
	def clear(self):
		del self.lines[:self.pos]
	
	def __bool__(self):
		self.clear_empty_lines()
		return bool(self.lines)

class SynergyFile(list):
	def __init__(self,filename,encoding="iso-8859-1"):
		super().__init__()
		self.new_read()
		
		with open(filename,"r",encoding=encoding) as f:
			self.line_buffer = LineBuffer(f.read().splitlines())
		
		self.parse_file()
	
	def parse_file(self):
		while self.line_buffer:
			for parser in (
					self.parse_raw_data_1,
					self.parse_procedure,
					self.parse_metadata,
				):
				try:
					parser()
				except FormatMismatch:
					continue
				else:
					break
	
	def new_read(self):
		self.append(SynergyRead())
	
	def parse_metadata(self):
		new_metadata = {}
		for line in self.line_buffer:
			if line == "":
				break
			elif line.count("\t") != 1:
				raise FormatMismatch
			else:
				key,_,value = line.partition("\t")
				if key.endswith(":"):
					key = key[:-1]
				new_metadata[key] = value
		
		self.add_metadata(**new_metadata)
		self.line_buffer.clear()
	
	def add_metadata(self,**metadata):
		if any( key in self[-1].metadata for key in metadata ):
			raise RepeatingData
		
		for key,value in metadata.items():
			if key=="Software Version":
				value = tuple( int(x) for x in value.split(".") )
			
			self[-1].metadata[key] = value
	
	def parse_procedure(self):
		line_iter = iter(self.line_buffer)
		if next(line_iter)!="Procedure Details" or next(line_iter)!="":
			raise FormatMismatch
		
		procedure = []
		while line:=next(line_iter):
			procedure.append(line)
		self.add_metadata( procedure = "\n".join(procedure) )
		self.line_buffer.clear()
	
	def parse_gain_values(self):
		pass

	def parse_results(self):
		pass
	
	def parse_raw_data_1(self):
		line_iter = iter(self.line_buffer)
		channel = next(line_iter)
		if "\t" in channel or next(line_iter)!="":
			raise FormatMismatch
		
		fields = next(line_iter).split("\t")
		if len(fields)<3 or fields[0]!="Time" or fields[1]!="T° "+channel:
			raise FormatMismatch
		wells = fields[2:]
		
		results = []
		while line:=next(line_iter):
			time,temperature,*numbers = line.split("\t")
			if len(numbers)!=len(wells):
				raise FormatMismatch
			try:
				result = to_seconds(time),float(temperature),*map(float,numbers)
			except ValueError:
				raise FormatMismatch
			results.append(result)
		
		for time,temperature,*numbers in results:
			self[-1].add_temperature(time,channel,temperature)
			for well,number in zip(wells,numbers):
				self[-1].add_result(time,channel,well,number)
		
		self.line_buffer.clear()


