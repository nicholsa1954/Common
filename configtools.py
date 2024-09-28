import configparser

def GetConfiguration(filename, node_name, leaf_name):
	parser = configparser.ConfigParser()
	parser.read(filename)
	return parser[node_name][leaf_name]