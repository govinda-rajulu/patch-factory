#!/usr/bin/env python3
"""Read-only retention preview. There is deliberately no deletion/apply mode.

Protect two newest dated releases per configured prefix, plus frozen/manual or
ambiguous entries. Candidates need human review: body markers are not provenance.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re
import subprocess
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'build'))
from build_identity import parse as parse_build_suffix

FROZEN = {'truecaller-v26.10.6'}
CI_MARKER = 'Built in public CI with [morphe-desktop](https://github.com/MorpheApp/morphe-desktop).'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def stamp(value):
    require(isinstance(value, str), 'missing release timestamp')
    d = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(d.tzinfo is not None, 'release timestamp lacks timezone')
    return d.timestamp()


def inventory(repo):
    require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo), 'unsafe repository')
    rows = [];seen = set()
    for page in range(1, 101):
        r = subprocess.run(['gh', 'api', 'repos/'+repo+'/releases?per_page=100&page='+str(page)],
                           capture_output=True, text=True, timeout=120)
        require(r.returncode == 0, 'release inventory read failed; no partial preview emitted')
        data = json.loads(r.stdout)
        require(isinstance(data, list), 'release API returned non-array')
        for row in data:
            require(isinstance(row, dict) and type(row.get('id')) is int and row['id'] not in seen,
                    'invalid/duplicate release id across pages')
            seen.add(row['id']);rows.append(row)
        if len(data) < 100:
            return rows
    raise ValueError('release inventory exceeded bounded pagination; no partial preview')


def release_shape(row, target, repo, version):
    """Classify metadata only. Never fetch evidence bodies or grant delete rights."""
    assets=row['assets'];body=row.get('body') or '';tag=row['tag_name']
    legacy=(len(assets)==1 and isinstance(assets[0],dict)
            and isinstance(assets[0].get('name'),str)
            and assets[0]['name'].endswith('-v'+version+'-arm64-v8a.apk')
            and type(assets[0].get('size')) is int and assets[0]['size']>1000000)
    # Preserve historical single-APK review behavior, except malformed structured
    # metadata must never be laundered through the legacy path.
    structured='[pf-release-v1]' in body
    if legacy and CI_MARKER in body and not structured:
        return 'legacy-single-apk',None
    ident=target['id']
    receipt='pf-publication-v1-'+ident+'.json'
    qualified='pf-qualified-v1-'+ident+'.json'
    expected_apk=(target.get('apk_name') or ident)+'-v'+version+'-arm64-v8a.apk'
    if not 2<=len(assets)<=3:
        return 'unrecognized','unexpected asset inventory'
    names=[];asset_ids=set()
    for a in assets:
        if not isinstance(a,dict):
            return 'unrecognized','invalid asset metadata'
        name=a.get('name');aid=a.get('id')
        if (not isinstance(name,str) or type(aid) is not int or aid<=0 or aid in asset_ids or
                name in names or name not in (expected_apk,receipt,qualified) or
                a.get('state')!='uploaded' or
                a.get('browser_download_url')!='https://github.com/'+repo+'/releases/download/'+tag+'/'+name or
                type(a.get('size')) is not int or a['size']<=0 or
                a.get('digest') is not None and not re.fullmatch(r'sha256:[0-9a-f]{64}',str(a['digest']))):
            return 'unrecognized','invalid or unexpected evidence asset metadata'
        if name!=expected_apk and a['size']>2*1024*1024:
            return 'unrecognized','oversized evidence metadata'
        names.append(name);asset_ids.add(aid)
    if set(names) not in ({expected_apk,receipt},{expected_apk,receipt,qualified}):
        return 'unrecognized','publication receipt missing or evidence set incomplete'
    apk=next(a for a in assets if a['name']==expected_apk)
    if apk['size']<=1000000:
        return 'unrecognized','invalid APK size'
    if structured:
        try:
            import release_notes
            info=release_notes.decode(body,tag,ident)
            require(info['version']==version and info['apk']==expected_apk and
                    info['bytes']==apk['size'] and
                    apk.get('digest')=='sha256:'+info['sha256'],
                    'structured summary / asset mismatch')
            require(row.get('author',{}).get('login')=='github-actions[bot]' and
                    row.get('author',{}).get('id')==41898282,
                    'structured publisher unknown')
        except (ValueError,KeyError,TypeError,AttributeError,RecursionError):
            return 'unrecognized','invalid or unbound structured release summary'
        return 'structured-apk-with-evidence',None
    if CI_MARKER in body:
        return 'legacy-apk-with-evidence',None
    return 'unrecognized','manual or ambiguous provenance'


def inventory_fingerprint(rows):
    """Bind all observed release/asset metadata, including body, hashes and IDs."""
    ordered=sorted(rows,key=lambda r:r['id'])
    return hashlib.sha256(json.dumps(ordered,sort_keys=True,separators=(',',':'),
                                     ensure_ascii=True,allow_nan=False).encode()).hexdigest()


def preview(rows, targets, repo, prefix=None):
    require(re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo), 'unsafe repository')
    require(isinstance(rows, list) and isinstance(targets, list) and targets, 'invalid input inventories')
    prefixes = [t.get('tag_prefix') or t['id'] for t in targets]
    require(len(prefixes) == len(set(prefixes)) and all(re.fullmatch('[a-z0-9-]+', p) for p in prefixes),
            'invalid/duplicate target prefixes')
    require(prefix is None or prefix in prefixes, 'unknown requested prefix')
    known = set(prefixes);by_prefix=dict(zip(prefixes,targets));groups = {};protected = [];candidates = [];ids=set();tags=set()
    for row in rows:
        require(isinstance(row, dict) and type(row.get('id')) is int, 'invalid release record')
        tag = row.get('tag_name');rid=row['id']
        require(isinstance(tag, str) and tag and not any(ord(c)<32 for c in tag), 'invalid release tag')
        require(rid not in ids and tag not in tags, 'duplicate release id/tag')
        ids.add(rid);tags.add(tag)
        require(isinstance(row.get('assets'),list),'missing asset inventory')
        item={'release_id':rid, 'tag':tag, 'url':row.get('html_url'), 'asset_count':len(row['assets'])}
        url=item['url']
        require(isinstance(url,str) and url.startswith('https://github.com/'+repo+'/releases/tag/'), 'unexpected release URL')
        require(type(row.get('draft')) is bool and type(row.get('prerelease')) is bool
                and isinstance(row.get('assets'),list), 'incomplete release metadata')
        match=re.fullmatch(r'([a-z0-9-]+)-v([0-9]+(?:[.][0-9]+)*)-b([0-9]{8}(?:[0-9]{26})?)',tag)
        reason=None
        if tag in FROZEN:reason='explicit frozen tag'
        elif not match or match[1] not in known:reason='manual, unknown-prefix or nonstandard tag'
        elif prefix is not None and match[1]!=prefix:reason='outside requested prefix'
        elif row['draft'] or row['prerelease']:reason='draft/prerelease protected'
        else:
            try:parse_build_suffix('-b'+match[3])
            except ValueError:reason='invalid date tag protected'
        if reason:
            protected.append(dict(item,reason=reason));continue
        item.update(prefix=match[1],published_at=row.get('published_at'))
        published=stamp(row.get('published_at'))
        # Rank by numeric build suffix (date, run id, attempt), then publication time/id. A manually
        # uploaded dated release is kept if it is among the newest two too.
        body=row.get('body') or ''
        require(isinstance(body,str), 'invalid release body')
        marked=any(word in body.lower() for word in ('frozen','manual','keep forever','do not delete','retention: keep'))
        shape,shape_protection=release_shape(row,by_prefix[match[1]],repo,match[2])
        item['metadata_shape']=shape
        item['protection']=('explicit keep/manual marker' if marked else shape_protection)
        groups.setdefault(match[1],[]).append((match[3],published,rid,item))
    for p,group in sorted(groups.items()):
        ordered=sorted(group,key=lambda x:x[:3],reverse=True)
        for i,(_,_,_,item) in enumerate(ordered):
            reason=item.pop('protection')
            if i<2:reason='two newest dated releases' + ('; '+reason if reason else '')
            if reason:protected.append(dict(item,reason=reason))
            else:candidates.append(dict(item,reason='older dated CI-marked release; human provenance review required'))
    protected.sort(key=lambda x:x['tag']);candidates.sort(key=lambda x:x['tag'])
    plan={'schema':1,'mode':'preview-only','repository':repo,'prefix':prefix,'inventory_count':len(rows),
          'keep_dated_per_prefix':2,'protected':protected,'candidates':candidates,
          'candidate_count':len(candidates),'candidate_asset_count':sum(x['asset_count'] for x in candidates),
          'deletion_authorized':False,
          'inventory_fingerprint':inventory_fingerprint(rows),
          'limits':'Metadata shapes and structured summaries are not independent provenance. Evidence JSON contents are not fetched or verified. Manual dated tags can copy CI metadata. Review exact candidates and backups before separately approved deletion. No apply command exists here.'}
    plan['fingerprint']=hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return plan


def summary(plan):
    lines=['## Release retention: preview only','',
           str(plan['candidate_count'])+' older release(s) proposed for review; '+str(len(plan['protected']))+' protected. Nothing deleted.',
           '', 'Approval is required separately. Frozen/manual or ambiguous entries are protected.', '']
    # Show plain escaped tag text, not arbitrary release-body HTML.
    for item in plan['candidates']:
        tag=item['tag'].replace('`','')
        lines.append('- `'+tag+'` ('+str(item['asset_count'])+' asset(s))')
    return '\n'.join(lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',required=True)
    parser.add_argument('--prefix')
    parser.add_argument('--targets',default='src/targets.json')
    parser.add_argument('--inventory',help='Optional saved JSON inventory; otherwise read GitHub')
    parser.add_argument('--output',help='Write the complete preview JSON to this local file')
    parser.add_argument('--summary',help='Append a read-only preview to this local summary file')
    args=parser.parse_args()
    targets=json.loads(pathlib.Path(args.targets).read_text())
    rows=json.loads(pathlib.Path(args.inventory).read_text()) if args.inventory else inventory(args.repo)
    result=preview(rows,targets,args.repo,args.prefix)
    encoded=json.dumps(result,sort_keys=True,indent=2)+'\n'
    if args.output:pathlib.Path(args.output).write_text(encoded)
    if args.summary:
        with pathlib.Path(args.summary).open('a') as f:f.write(summary(result))
    print(encoded,end='')


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,TypeError,OSError,subprocess.TimeoutExpired) as error:
        raise SystemExit('RETENTION_PREVIEW_FAILED: '+str(error))
