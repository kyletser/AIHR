import paramiko, os, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('150.158.89.70', 22, 'root', 'LXPzxy2002115', timeout=10)

# Upload main.py
sftp = ssh.open_sftp()
sftp.put(r'E:\Desktop\AIHR\backend\main.py', '/opt/offercatcher/main.py')
print('main.py OK')

# Upload static
ssh.exec_command('rm -rf /opt/offercatcher/static/* && mkdir -p /opt/offercatcher/static/assets')
sftp.put(r'E:\Desktop\AIHR\backend\static\index.html', '/opt/offercatcher/static/index.html')
for f in os.listdir(r'E:\Desktop\AIHR\backend\static\assets'):
    sftp.put(r'E:\Desktop\AIHR\backend\static\assets\\'+f, '/opt/offercatcher/static/assets/'+f)
sftp.close()
print('static OK')

# Restart
stdin, stdout, stderr = ssh.exec_command("ss -tlnp | grep 8088 | grep -oP 'pid=\\K\\d+'", timeout=10)
pid = stdout.read().decode().strip()
if pid:
    ssh.exec_command('kill {}'.format(pid))
time.sleep(2)
ssh.exec_command('cd /opt/offercatcher && nohup venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8088 > /tmp/oc.log 2>&1 &')
time.sleep(5)

# Verify
stdin, stdout, stderr = ssh.exec_command('curl -s http://localhost:8088/api/health', timeout=10)
print('Health:', stdout.read().decode()[:100])

ssh.close()
print('Done')
