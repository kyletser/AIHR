import paramiko, os, time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('150.158.89.70', 22, 'root', 'LXPzxy2002115', timeout=10)

# Clean and recreate
ssh.exec_command('rm -rf /opt/offercatcher/static/* && mkdir -p /opt/offercatcher/static/assets')

sftp = ssh.open_sftp()
static = r'E:\Desktop\AIHR\backend\static'

# Upload index.html
sftp.put(f'{static}/index.html', '/opt/offercatcher/static/index.html')

# Upload all assets with new hashes
for f in os.listdir(f'{static}/assets'):
    sftp.put(f'{static}/assets/{f}', f'/opt/offercatcher/static/assets/{f}')
    print(f'  {f}')

sftp.close()

# Kill old, restart (port 8088 only)
stdin, stdout, stderr = ssh.exec_command("ss -tlnp | grep 8088 | grep -oP 'pid=\\K\\d+'", timeout=10)
pid = stdout.read().decode().strip()
if pid:
    ssh.exec_command(f'kill {pid}')
time.sleep(2)
ssh.exec_command('cd /opt/offercatcher && nohup venv/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8088 > /tmp/oc.log 2>&1 &')
time.sleep(4)

# Verify
stdin, stdout, stderr = ssh.exec_command("curl -s http://localhost:8088/login | grep -o 'LoginView-[^.]*'", timeout=10)
ver = stdout.read().decode().strip()
print(f'\nLoginView version on server: {ver}')

# Test login
stdin, stdout, stderr = ssh.exec_command(
    "curl -s -X POST http://localhost:8088/api/login -H 'Content-Type: application/json' -d '{\"username\":\"admin\",\"password\":\"admin\"}' | python3 -c 'import sys,json; print(json.load(sys.stdin).get(\"username\",\"FAIL\"))'",
    timeout=10
)
print(f'Login test: {stdout.read().decode().strip()}')

ssh.close()
print('\nDone. http://150.158.89.70:8088 | admin/admin')
