import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import source_fallback_contracts as ff
import test_source_inputs as sf
import test_identity as identity_fixtures
import source_fallback as fb
import source_inputs as source
import artifact_identity as identity
import input_recipe
import shadow_inputs as shadow


class FallbackProvenance(unittest.TestCase):
    def setUp(self):
        self.f=sf.SourceContracts();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.root=self.f.r
        self.raw=self.root/'fixture-original.apk';self.raw.write_bytes(ff.apk_bytes())
        self.a={'source':'apkmirror','version_name':'4.2.1','version_code':'42',
                'container':fb.file_record(self.raw),'certificate_sha256':ff.CERT,
                'mapping':{'list_url':'https://www.apkmirror.com/uploads/?appcategory=key-mapper',
                           'org':'fixture-org','name':'key-mapper'},
                'evidence':'docs/review/source-qualifications/keymapper-fixture.json'}
        self.a['variant']={'kind':'apk','abis':[],'min_sdk':29,
                           'apkmirror_url':'https://www.apkmirror.com/apk/fixture-org/key-mapper/'
                           'key-mapper-4-2-1-release/key-mapper-fixture-android-apk-download/'}
        doc=json.loads((self.root/fb.POLICY).read_text());doc['targets']['keymapper']['admissions']=[self.a]
        (self.root/fb.POLICY).write_text(json.dumps(doc))
        ev={'schema':1,'target':'keymapper','package':'io.github.sds100.keymapper',
            'source':self.a['source'],'version_name':'4.2.1','version_code':'42',
            'container':self.a['container'],'certificate_sha256':ff.CERT,
            'publisher_anchor_reviewed':True,'variant_compatibility_reviewed':True}
        ev['variant']=self.a['variant']
        e=self.root/self.a['evidence'];e.parent.mkdir(exist_ok=True);e.write_text(json.dumps(ev))
        self.receipt={'schema':1,'target':'keymapper','source':'apkmirror','requested_version':'4.2.1',
                      'original':{'container':self.a['container'],'splits':[self.a['container']],
                                  'standalone':True,'abis':[],'certificate_sha256':ff.CERT},
                      'patcher_input':self.a['container'],'limits':fb.LIMITS}

    def downloader(self,args,**kwargs):
        d=self.root/'download';d.mkdir();(d/'key-mapper.apk').write_bytes(self.raw.read_bytes())
        (self.root/fb.RECEIPT).write_text(json.dumps(self.receipt))
        return subprocess.CompletedProcess(args,0)

    def prepare(self):
        self.f.f.prepare('keymapper')
        return source.prepare(self.root,'keymapper',self.f.env,self.downloader,lambda *args:self.f.meta)

    def consume(self):
        doc=self.prepare()
        (self.root/'download').rename(self.root/'producer-download')
        (self.root/fb.RECEIPT).rename(self.root/'producer-receipt.json')
        installed=source.install(self.root,'keymapper',self.f.env)
        self.assertEqual(doc,installed)
        return doc

    def test_prepared_lock_carries_fallback_proof_and_install_restores_it(self):
        doc=self.consume()
        self.assertEqual(doc['fallback'],self.receipt)
        self.assertEqual(fb.read_receipt(self.root,'keymapper',doc['apk']),self.receipt)
        self.assertEqual(source.verify(self.root,'keymapper',self.f.env),doc)

    def test_receipt_tampering_wrong_target_source_bytes_signer_abi_refused(self):
        for mutate in (lambda d:d.update(target='reddit'),lambda d:d.update(source='apkpure'),
                       lambda d:d['patcher_input'].update(sha256='0'*64),
                       lambda d:d['original'].update(certificate_sha256='2'*64),
                       lambda d:d['original'].update(abis=['x86']),
                       lambda d:d.update(limits=[]),lambda d:d.update(extra='unexpected')):
            bad=copy.deepcopy(self.receipt);mutate(bad)
            with self.assertRaises(ValueError):fb.validate_receipt(self.root,'keymapper',bad,self.a['container'])

    def test_resealed_packet_with_changed_fallback_refuses(self):
        doc=self.prepare();bad=copy.deepcopy(doc);bad['fallback']['source']='apkpure'
        (self.root/source.LOCK).write_bytes(input_recipe.canonical(shadow.seal({k:v for k,v in bad.items() if k!='sha256'})))
        with self.assertRaises(ValueError):source.verify(self.root,'keymapper',self.f.env)

    def test_existing_consumer_receipt_refuses_before_install(self):
        self.prepare();(self.root/'download').rename(self.root/'producer-download')
        before=(self.root/fb.RECEIPT).read_bytes()
        with self.assertRaisesRegex(ValueError,'existing fallback receipt'):
            source.install(self.root,'keymapper',self.f.env)
        self.assertFalse((self.root/'download').exists());self.assertEqual((self.root/fb.RECEIPT).read_bytes(),before)

    def test_direct_capture_and_final_report_bind_receipt_and_detect_removal(self):
        f=identity_fixtures.Identity();f.setUp();self.addCleanup(f.tearDown)
        f.capture_fixture()
        # Transfer the synthetic qualification, input and proof before recapturing.
        (f.r/fb.POLICY).write_bytes((self.root/fb.POLICY).read_bytes())
        e=f.r/self.a['evidence'];e.parent.mkdir(exist_ok=True);e.write_bytes((self.root/self.a['evidence']).read_bytes())
        (f.r/'download/key-mapper.apk').write_bytes(self.raw.read_bytes())
        (f.r/fb.RECEIPT).write_text(json.dumps(self.receipt))
        with contextlib.redirect_stdout(io.StringIO()):identity.capture_inputs(f.r,'keymapper','lain',f.env)
        captured=json.loads((f.r/'.build-inputs.json').read_text())
        self.assertEqual(captured['source_fallback'],self.receipt)
        report=f.verify_fixture()
        self.assertEqual(report['inputs']['source_fallback'],self.receipt)
        (f.r/fb.RECEIPT).rename(f.r/'preserved-receipt.json')
        with self.assertRaisesRegex(ValueError,'fallback provenance changed'):f.verify_fixture()


if __name__=='__main__':unittest.main()
