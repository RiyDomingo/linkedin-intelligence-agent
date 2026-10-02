from pathlib import Path
import asyncio,json,tempfile,sys,subprocess,os,hashlib
r=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(r/'tools/linkedin'),str(r/'skills/li-read/scripts'),str(r/'skills/li-context/scripts')]
from gateway import Gateway
from policy import set_enabled,begin_task
from account_context import retain
import professional_memory as m
class SyntheticUpstream:
 def __init__(self):self.calls=[]
 async def call(self,name,args):
  self.calls.append(name)
  return {'url':'https://www.linkedin.com/in/alex-example/','sections':{'main_profile':'Alex Example — Research Engineer','experience':'Research Engineer at Sample Robotics Ltd., current','posts':'Testing robotics prototypes starts with measurement.','feed':'Public standards discussion on measurement.'}}
 async def close(self):pass

import unittest

class MemoryOnboardingAcceptance(unittest.TestCase):
 def test_fresh_onboarding_then_offline_second_process(self):
  with tempfile.TemporaryDirectory(prefix='memory-onboarding-') as tmp:
   root=Path(tmp)/'.linkedin-agent';set_enabled(root,True);begin_task(root,onboarding=True);up=SyntheticUpstream();g=Gateway(root,up)
   p=asyncio.run(g.dispatch('read_my_profile',{'stage':'experience'}))
   retain(root,{'receipt_id':p['receipt_id'],'items':[{'data':{'name':'Alex Example','headline':'Research Engineer','roles':['Research Engineer at Sample Robotics Ltd., current'],'education':['Example University'],'skills':['Python']}}]})
   source=next(s for s in m.sources(root) if s['kind']=='linkedin')
   m.ingest(root,source['id'],[{'field':'current_roles','value':'Research Engineer','key':'primary'}])
   p=asyncio.run(g.dispatch('read_my_posts',{'stage':'onboarding'}))
   retain(root,{'receipt_id':p['receipt_id'],'items':[{'data':{'text':'Testing robotics prototypes starts with measurement.','author':'Alex Example','url':None}}],
   'summary':{'voice':[{'text':'Short, technical explanatory sentences','label':'INFERRED'}],'themes':[{'text':'Robotics and measurement','label':'INFERRED'}]}})
   resume=Path(tmp)/'resume.md';resume.write_text('Alex Example. Senior Engineer at Sample Robotics Ltd. Example University. Python.')
   s=m.add_document(root,resume);m.ingest(root,s['source_id'],[{'field':'current_roles','key':'primary','value':'Senior Engineer'},{'field':'education','key':'university','value':'Example University'},{'field':'expertise','key':'robotics','value':'Robotics prototyping','kind':'EXPERTISE','level':'experienced_in'}])
   s=m.add_bio(root,'Building dependable robots for research and product teams.');m.ingest(root,s['source_id'],[{'field':'positioning','key':'primary','value':'Building dependable robots','kind':'POSITIONING'}])
   receipt={'source_type':'PUBLIC_WEB','url':'https://example.org/','content':'Alex Example is a consultant working on robotics.','retrieved_at':m.now()}
   s=m.add_web_evidence(root,receipt['url'],receipt,'Synthetic user-linked website',items=[{'field':'current_roles','key':'primary','value':'Consultant'},{'field':'interests','key':'robotics','value':'Robotics','kind':'INTEREST'}])
   roles=next(x for x in m.summary(root,include_evidence=True)['context'] if x['field']=='current_roles')
   assert roles['conflict'] and len(roles['evidence'])==3 and roles['preferred']['label']=='USER_DOCUMENT'
   m.correct(root,'audiences','primary','Researchers and product development partners')
   set_enabled(root,False);before_calls=len(up.calls)
   script=r/'skills/li-context/scripts/professional_memory.py';before=hashlib.sha256((root/'memory/store.json').read_bytes()).hexdigest()
   env={**os.environ,'LINKEDIN_ACCOUNT_CONNECTOR_ENABLED':'false'}
   def query(fields):
    return json.loads(subprocess.run([sys.executable,str(script),'--root',str(root),'show','--fields',*fields],env=env,capture_output=True,text=True,check=True).stdout)
   content=query(['voice_patterns','content_topics','expertise','claims']);profile=query(['current_roles','experience','education','positioning']);daily=query(['interests','audiences','content_topics'])
   assert all(x['context'] for x in (content,profile,daily))
   assert next(x for x in daily['context'] if x['field']=='audiences')['preferred']['label']=='USER_CONFIRMED'
   assert before==hashlib.sha256((root/'memory/store.json').read_bytes()).hexdigest();assert len(up.calls)==before_calls
   pass
