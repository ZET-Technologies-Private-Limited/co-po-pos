import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
data=open('app/api/v1/routes.py','rb').read().lstrip(b'\xef\xbb\xbf').decode('utf-8','replace')
lines=data.splitlines()
for i,l in enumerate(lines[4560:4610],4561):
    print(f"{i}|{l}")
