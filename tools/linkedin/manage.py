#!/usr/bin/env python3
"""Explicit local controls. No passwords, cookies, login or upstream requests."""
import argparse
import json
from policy import begin_task, enabled, set_enabled


def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('--root',default='.linkedin-agent')
    sub=ap.add_subparsers(dest='action',required=True)
    for name in ('enable','disable','status'): sub.add_parser(name)
    t=sub.add_parser('begin-task'); t.add_argument('--onboarding',action='store_true')
    a=ap.parse_args()
    if a.action in ('enable','disable'):
        set_enabled(a.root,a.action=='enable'); result={'enabled':enabled(a.root),'authentication_deleted':False}
    elif a.action=='begin-task': result=begin_task(a.root,a.onboarding)
    else: result={'enabled':enabled(a.root)}
    print(json.dumps(result,indent=2))


if __name__=='__main__': main()
