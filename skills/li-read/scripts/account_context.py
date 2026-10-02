#!/usr/bin/env python3
"""Persist agent-normalized account evidence and labelled summaries; no network/auth."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
from read_layer import ingest, atomic_save
from models import normalize_envelope, parse_time
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'li-context/scripts'))
from context import safe_path, read_text
from professional_memory import sync_account, check_account_identity

PROVIDER='linkedin-account-v1'
TTL={'profile':30*86400,'own_posts':3*86400,'feed':3600}


def reject_secrets(value):
    text=json.dumps(value,ensure_ascii=False)
    if re.search(r'(?i)(?:bearer\s+\S+|(?:li_at|jsessionid|password|cookie|authorization|access_token)\s*["\s]*[:=])',text):
        raise ValueError('Credential-like material refused')


def retain(root,payload):
    if not isinstance(payload,dict) or set(payload)-{'receipt_id','items','summary'}:
        raise ValueError('Only receipt_id, normalized items and summary accepted')
    rid=payload.get('receipt_id','')
    if not isinstance(rid,str) or not re.fullmatch('[0-9a-f]{64}',rid): raise ValueError('Actual gateway receipt required')
    receipt=json.loads(read_text(safe_path(root,'account/receipts/'+rid+'.json')))
    cap=receipt['capability']
    if cap not in TTL or receipt['state'] not in ('SUCCESS','PARTIAL_READ'):
        raise ValueError('Successful/partial account receipt required')
    if cap in ('profile','own_posts'):check_account_identity(root,receipt.get('source_url'))
    items=payload.get('items',[])
    if not isinstance(items,list) or len(items)> (20 if cap=='feed' else 30): raise ValueError('Bounded normalized records required')
    reject_secrets(payload)
    records=[]
    for original in items:
        if not isinstance(original,dict) or set(original)-{'data','assessment'}: raise ValueError('Normalized data/assessment only')
        data=dict(original.get('data',{}))
        if cap=='profile':
            kind='profile'; data['url']=receipt.get('source_url'); identifier='own-profile'
        else:
            kind='post'
            # Upstream section text plus unordered links supplies no trusted mapping.
            # A future validated association adapter may enable specific permalinks.
            if data.get('url') is not None: raise ValueError('Unverified post permalink refused')
            data['url']=None
            text=data.get('text')
            if not isinstance(text,str) or not text.strip(): raise ValueError('Observed post body required')
            identifier='local-observation-'+hashlib.sha256(text.encode()).hexdigest()
        records.append({'kind':kind,'capability':cap,'id':identifier,'data':data,'assessment':original.get('assessment',{})})
    # Duplicate visible bodies are one local observation, never a LinkedIn ID.
    unique={r['id']:r for r in records}
    env={'schema_version':1,'source':{'type':'connector','provider':PROVIDER,'identifier':rid,
         'url':receipt.get('source_url'),'retrieved_at':receipt['retrieved_at'],'visibility':'unknown'},
         'capabilities':[cap],'coverage':'partial','items':list(unique.values())}
    normalize_envelope(env)
    summary=payload.get('summary')
    if summary is not None:
        if not isinstance(summary,dict) or set(summary)-{'career','interests','voice','themes','incomplete_sections'}:
            raise ValueError('Unsupported summary fields')
        for key, entries in summary.items():
            if not isinstance(entries,list): raise ValueError('Labelled summary lists required')
            for entry in entries:
                if not isinstance(entry,dict) or set(entry)!={'text','label'} or not isinstance(entry['text'],str): raise ValueError('Summary text/label required')
                if entry['label'] not in ('OBSERVED','INFERRED'): raise ValueError('Account summaries cannot assert USER_CONFIRMED or PUBLIC_WEB')
                if key in ('voice','themes') and entry['label']!='INFERRED': raise ValueError('Voice/theme assessment is inference')
    counts=ingest(root,env)
    atomic_save(root,'account/observations/'+rid+'.json',env)
    if summary is not None:
        atomic_save(root,'account/summaries/'+rid+'.json',{'retrieved_at':receipt['retrieved_at'],
                    'receipt_id':rid,'capability':cap,'summary':summary})
    sync_account(root)
    # Never touches curated identity/knowledge files or confirmed publication logs.
    return {'retained':len(unique),'counts':counts,'receipt_id':rid,'confirmed_publication':False}


def refresh_plan(root,needs,force=False,current=None):
    if any(c not in TTL for c in needs): raise ValueError('Unsupported account capability')
    current=current or datetime.now(timezone.utc)
    folder=safe_path(root,'account/observations')
    dates={}
    for p in folder.glob('*.json') if folder.exists() else []:
        env=json.loads(read_text(safe_path(root,'account/observations/'+p.name)))
        normalize_envelope(env)
        if not env['items']:
            rid=env['source']['identifier']
            if not re.fullmatch('[0-9a-f]{64}',rid): continue
            receipt=json.loads(read_text(safe_path(root,'account/receipts/'+rid+'.json')))
            if receipt.get('section_status',{}).get('posts')!='EMPTY_OBSERVED': continue
        when=parse_time(env['source']['retrieved_at'])
        for c in env['capabilities']:
            if c in TTL: dates[c]=max(dates.get(c,when),when)
    report={}
    for c in dict.fromkeys(needs):
        age=(current-dates[c]).total_seconds() if c in dates else None
        report[c]={'age_hours':None if age is None else round(age/3600,2),
                   'refresh':force or age is None or age<0 or age>=TTL[c],
                   'mode':'LOCAL_CACHE' if age is not None else 'ACCOUNT_CONNECTED'}
    return report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',default='.linkedin-agent')
    sub=ap.add_subparsers(dest='action',required=True)
    p=sub.add_parser('retain');p.add_argument('file')
    p=sub.add_parser('refresh-plan');p.add_argument('--needs',nargs='*',default=[]);p.add_argument('--force',action='store_true')
    a=ap.parse_args()
    try:
        result=retain(a.root,json.loads(Path(a.file).read_text())) if a.action=='retain' else refresh_plan(a.root,a.needs,a.force)
        print(json.dumps(result,indent=2))
    except (OSError,ValueError,KeyError,TypeError) as exc:
        ap.exit(2,'Account context: invalid or unavailable local input; no credential diagnostics emitted\n')


if __name__=='__main__': main()
