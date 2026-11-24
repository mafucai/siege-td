#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量 AI 重画，带重试与进度保存。"""
import os, sys, json, time, subprocess

SRC='art/ai_src'; DST='art/ai_hd'
todo=json.load(open('/tmp/todo.json',encoding='utf-8'))
done_file='art/ai_hd/_done.json'
done=json.load(open(done_file,encoding='utf-8')) if os.path.exists(done_file) else {'ok':['castle_3'],'fail':[]}

os.makedirs(DST, exist_ok=True)
t0=time.time()
for i,item in enumerate(todo,1):
    name=item['out']
    if name in done['ok']:
        continue
    src=os.path.join(SRC,name+'.png')
    dst=os.path.join(DST,name+'.png')
    print('[%2d/%d] %-26s %3dx%-3d' % (i,len(todo),name,item['w'],item['h']), flush=True)
    ok=False
    for attempt in range(3):
        r=subprocess.run([sys.executable,'tools/ai_redraw.py',src,dst,'--scale','4'],
                         capture_output=True,text=True,timeout=500)
        if r.returncode==0 and os.path.exists(dst) and os.path.getsize(dst)>1000:
            ok=True
            break
        tail=(r.stdout+r.stderr).strip().split('\n')[-2:]
        print('    重试 %d: %s' % (attempt+1, ' | '.join(tail)), flush=True)
        time.sleep(5)
    if ok:
        done['ok'].append(name)
        print('    OK  %.0fs' % (time.time()-t0), flush=True)
    else:
        done['fail'].append(name)
        print('    失败', flush=True)
    json.dump(done,open(done_file,'w',encoding='utf-8'),ensure_ascii=False,indent=2)

print()
print('完成 %d/%d，失败 %d，耗时 %.0fs' % (len(done['ok'])-1, len(todo), len(done['fail']), time.time()-t0))
