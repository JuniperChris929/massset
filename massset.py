# Developed by Christian Scholz [Mail: chs@ip4.de, Mastodon: @chsjuniper@mastodon.social, Twitter: @chsjuniper]
# Feel free to use and modify this script as needed but use at your own risk!
# This is a hobby project - I'm not employed by Juniper.
# I just wanted a tool that helps me doing my every day work a bit faster and more consistent
# You've been warned ;)

import sys
import time
import getpass
import logging
import paramiko
import openpyxl
from scp import SCPClient
from datetime import datetime
from colorama import Fore
import os.path

if os.path.isfile('iplist.xlsx'):
    print("iplist.xlsx found - using hosts from file")
    varIP = "127.0.0.1"
elif os.path.isfile('iplist.txt'):
    print("iplist.txt found - using hosts from file")
    varIP = "127.0.0.1"
else:
    print("Neither iplist.xlsx not iplist.txt found - entering single Device Mode.")
    varIP = input("Please enter the Hostname or IP of your target Device: ")

varUser = input("Please Enter a Username (not root): ")
varPassword = getpass.getpass()

version_arg = "1.0.9.102902"
now = datetime.now()
date_arg = now.strftime("%Y-%m-%d_%H-%M-%S")

# Set up logging
log = "logfile_" + date_arg + ".log"
logging.basicConfig(filename=log, level=logging.DEBUG, format='%(asctime)s %(message)s', datefmt='%d/%m/%Y %H:%M:%S')

if str(varUser) == 'root':
    sys.exit(
        'Which part of NOT root did you not understand? - Please run the tool again and choose another user.')

buff = ''
resp = ''

print("\n")
print("\n")
print("\n")
print("###############################################################################")
print("#                          Version:", version_arg, "                          #")
print("#            WARNING: Please leave this Window open and running.              #")
print("#      After the Program is finished, it will automatically close itself.     #")
print("###############################################################################")
print("\n")
print("\n")
print("\n")
print("Script is starting...")
logging.info('Script is starting...')
time.sleep(2)

def commands_to_run_per_device():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(varIP, username=varUser, password=varPassword)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    channel = ssh.invoke_shell()

    # Uploading the Software and showing the progress
    print("\n")
    print(f"Step 1: Uploading commandfile to Device {varIP}")
    logging.info('Step 1: Uploading commandfile to Device ' + varIP)

    def progress(filename, size, sent):
        sys.stdout.write(Fore.LIGHTGREEN_EX)
        sys.stdout.write("Upload in Progress: %.2f%%   \r" % (float(sent)/float(size)*100) )
        sys.stdout.write(Fore.RESET)

    try:
        with SCPClient(ssh.get_transport(), progress = progress, sanitize=lambda x: x) as scp:
            scp.put("commands.txt", '/var/tmp/')
    except:
        logging.info('Could not place file - something went wrong...')
        exit()
    finally:
        logging.info('File added successfully!')
        scp.close()

    # Saving the config
    print("\n")
    print("Step 2: Saving the active configuration in set-format (including secrets)")
    logging.info('Step2: Saving the active configuration in set-format (including secrets)')
    stdin, stdout, stderr = ssh.exec_command(
        'show configuration | display set | no-more | save /var/tmp/active-config-' + date_arg + '.txt\n')
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        logging.info('Info: Configuration saved successfully.')
    else:
        logging.info('Error: Could not save configuration.')

    # committing the config
    print("\n")
    print("Step 3: committing uploaded commands")
    logging.info('Step 3: committing uploaded commands')

    try: 
        remote_conn_pre = paramiko.SSHClient()
        remote_conn_pre.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        remote_conn_pre.connect(varIP, username=varUser, password=varPassword, look_for_keys=False, allow_agent=False)
        # print('SSH connection established to ' + varIP)
        logging.info('SSH connection established to ' + varIP)
        remote_conn = remote_conn_pre.invoke_shell()
        # print('Interactive SSH session established')
        logging.info('Interactive SSH session established')
        # Print terminal to screen
        output = remote_conn.recv(3000)
        remote_conn.send('\n')
        time.sleep(2)
        # print(output.decode())
        logging.info(output.decode())
        # Username root requires getting into the cli
        if varUser == 'root':
            remote_conn.send('cli\n')
            time.sleep(3)
            output = remote_conn.recv(3000)
            print(output.decode())
        else:
            pass
        # Enter configuration mode
        remote_conn.send('configure\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        # print(output.decode())
        logging.info(output.decode())
        # SNMP Configuration
        remote_conn.send('load set /var/tmp/commands.txt \n')
        time.sleep(30)
        output = remote_conn.recv(3000)
        # print(output.decode())
        logging.info(output.decode())
        # Save configuration
        remote_conn.send('commit comment "Commands loaded via Massscript (Python)" and-quit\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        # print(output.decode())
        logging.info(output.decode())
        print("Waiting 60s until commit has been executed. Please wait...")
        time.sleep(60)
        print("Success!")
        # Exit configuration mode
        remote_conn.send('exit\n')
        time.sleep(2)
        output = remote_conn.recv(3000)
        # print(output.decode())
        logging.info(output.decode())
        if varUser == 'root':
            remote_conn.send('exit\n')
            time.sleep(2)
            output = remote_conn.recv(3000)
            # print(output.decode())
            logging.info(output.decode())
        else:
            pass
    except paramiko.AuthenticationException as error:
        print("Error: The Credentials did not work or ssh is not enabled!")
        print("\n")
        print("\n")

    # Saving the config
    print("\n")
    print("Step 4: Saving the new configuration in set-format (including secrets)")
    logging.info('Step4: Saving the new configuration in set-format (including secrets)')
    stdin, stdout, stderr = ssh.exec_command(
        'show configuration | display set | no-more | save /var/tmp/new-config-' + date_arg + '.txt\n')
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        logging.info('Info: Configuration saved successfully.')
    else:
        logging.info('Error: Could not save configuration.')

    # Now downloading all the files created on the device via scp
    print("\n")
    print("Step 5: Fetching the files created earlier")
    logging.info('Step 5: Fetching the files created earlier')
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(varIP, username=varUser, password=varPassword)
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    channel = ssh.invoke_shell()

    try:
        with SCPClient(ssh.get_transport(), sanitize=lambda x: x) as scp:
            scp.get(remote_path='/var/tmp/active-config-' + date_arg + '.txt',
                    local_path='./')
    except:
        logging.info('Error: Could not fetch active Configuration - something went wrong...')
        scp.close()
    finally:
        logging.info('Info: Configuration successfully fetched.')
        scp.close()


    try:
        with SCPClient(ssh.get_transport(), sanitize=lambda x: x) as scp:
            scp.get(remote_path='/var/tmp/new-config-' + date_arg + '.txt',
                    local_path='./')
    except:
        logging.info('Error: Could not fetch active Configuration - something went wrong...')
        scp.close()
    finally:
        logging.info('Info: Configuration successfully fetched.')
        scp.close()

    print("\n")
    print("Step 6: Deleting files from remote device to gain space back and finishing script")
    logging.info('Step 6: Deleting files from remote device to gain space back and finishing script')
    logging.info('Info: Deleting /var/tmp/active-config-' + date_arg + '.txt')
    channel.send('file delete /var/tmp/active-config-' + date_arg + '.txt\n')
    logging.info('Info: File deleted successfully.')
    time.sleep(2)
    logging.info('Info: Deleting /var/tmp/new-config-' + date_arg + '.txt')
    channel.send('file delete /var/tmp/new-config-' + date_arg + '.txt\n')
    logging.info('Info: File deleted successfully.')
    time.sleep(2)
    logging.info('Info: Deleting /var/tmp/commands.txt')
    channel.send('file delete /var/tmp/commands.txt\n')
    logging.info('Info: File deleted successfully.')
    time.sleep(2)
    resp = channel.recv(9999)
    output = resp.decode().split(',')
    time.sleep(1)
    ssh.close()
    time.sleep(1)

if os.path.isfile('iplist.xlsx'):
    try:
        readbook = openpyxl.load_workbook("iplist.xlsx")
        sheet_switches = readbook["switches"]
        rows_switches = list(sheet_switches)
        rowcount = sheet_switches.max_row
        rowcounter = 1
    except Exception as err:
        exit()
    
    for row_active in range(1,rowcount):
        if rows_switches[row_active][0].value != "":
            try:
                varIP = str(rows_switches[row_active][0].value)
                commands_to_run_per_device()
            except Exception as err:
                exit()

elif os.path.isfile('iplist.txt'):
    with open('iplist.txt','r') as f:
        ip_not_found = True
        for line in f:
            ip_not_found = False
            varIP = str("{IP}".format(IP=line))
            commands_to_run_per_device()
        if ip_not_found:
            print("File iplist.txt found, but no ip inside... Aborting...")
            exit()

else:
    commands_to_run_per_device()

print("\n")
print("The Script has finished! Check Logs if needed.")