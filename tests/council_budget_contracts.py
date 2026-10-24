"""Council v4 contracts (packet W15h, 22 Oct 2026, owner: agents fail too often). The desk showed
seats lost to stale model ids, busy free tiers and reasoning cut at max_tokens. Seats now
discover catalogue models, fall back to other providers, retry a cut reply with more room,
and call one provider at a time with a published-limit gap."""
import importlib.util
import json
import threading
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('council_v4', ROOT / 'src/council/council.py')
council = importlib.util.module_from_spec(spec)
spec.loader.exec_module(council)

OK = json.dumps({'choices': [{'message': {'content': '{"summary": "ok", "verdict": "looks_ok", "findings": []}'}}]})
CUT = json.dumps({'choices': [{'finish_reason': 'length', 'message': {'content': ''}}]})
ENV = {'NVIDIA_API_KEY': 'nvapi-FAKE-0001', 'GROQ_API_KEY': 'gsk_FAKE_0002', 'PF_RETRY_SLEEP': '0',
       'PF_REPO': 'govinda-rajulu/patch-factory'}
SEAT = {'id': 's', 'provider': 'nvidia', 'models': ['m1', 'm2'], 'max_input_chars': 100000}


def fake(answer, catalog=()):
    asked = []

    def http(method, url, headers, body=None, timeout=90):
        if url.endswith('/models'):
            return 200, json.dumps({'data': [{'id': m} for m in catalog]})
        asked.append((url.split('/')[2], body['model'], body.get('max_tokens'), body.get('reasoning_effort')))
        return answer(url, body)
    return http, asked


class Seats(unittest.TestCase):
    def setUp(self):
        council._model_cache.clear()

    def test_backup_on_another_provider_answers_when_own_models_are_busy(self):
        http, asked = fake(lambda url, b: (503, 'busy') if 'nvidia' in url else (200, OK))
        council.http = http
        seat = dict(SEAT, backups=[{'provider': 'groq', 'model': 'g1'}, {'provider': 'cloudflare', 'model': '@cf/x'}])
        got = council.run_seat(seat, 's', 'u', ENV, council.check_review, 'C')
        self.assertEqual(got['status'], 'OK')
        self.assertEqual(got['model'], 'g1 via groq (backup)')
        self.assertNotIn('api.cloudflare.com', [a[0] for a in asked])  # no Cloudflare key: skipped

    def test_no_own_key_but_a_keyed_backup_still_runs(self):
        http, asked = fake(lambda url, b: (200, OK))
        council.http = http
        env = {k: v for k, v in ENV.items() if k != 'NVIDIA_API_KEY'}
        got = council.run_seat(dict(SEAT, backups=[{'provider': 'groq', 'model': 'g1'}]), 's', 'u', env, council.check_review, 'C')
        self.assertEqual((got['status'], [a[1] for a in asked]), ('OK', ['g1']))
        self.assertEqual(council.run_seat(SEAT, 's', 'u', env, council.check_review, 'C')['status'], 'SKIPPED_NO_KEY')

    def test_discover_adds_catalogue_models_after_the_list(self):
        http, asked = fake(lambda url, b: (404, 'model not found') if b['model'] in ('m1', 'm2') else (200, OK),
                           catalog=['nvidia/nemotron-4-super', 'nvidia/nemotron-3-super', 'other'])
        council.http = http
        got = council.run_seat(dict(SEAT, discover=['^nvidia/nemotron-[0-9]+-super']), 's', 'u', ENV, council.check_review, 'C')
        self.assertEqual(got['status'], 'OK')
        self.assertEqual([a[1] for a in asked], ['m1', 'm2', 'nvidia/nemotron-4-super'])

    def test_cut_reply_gets_one_retry_with_more_room_and_low_effort(self):
        http, asked = fake(lambda url, b: (200, OK) if b.get('max_tokens') == 8000 else (200, CUT))
        council.http = http
        got = council.run_seat(dict(SEAT, max_tokens=4000), 's', 'u', ENV, council.check_review, 'C')
        self.assertEqual((got['status'], got['model']), ('OK', 'm1 (more room)'))
        self.assertEqual(asked[1][2:], (8000, 'low'))

    def test_more_room_is_capped(self):
        http, asked = fake(lambda url, b: (200, CUT))
        council.http = http
        got = council.run_seat(dict(SEAT, max_tokens=8000), 's', 'u', ENV, council.check_review, 'C')
        self.assertTrue(got['status'].startswith('UNAVAILABLE'))
        self.assertLessEqual(max(a[2] for a in asked), 16000)


class Pacing(unittest.TestCase):
    def test_one_provider_is_called_one_at_a_time_with_a_gap(self):
        council._pace_last.clear()
        stamps, inside = [], []

        def http(method, url, headers, body=None, timeout=90):
            inside.append(1)
            self.assertEqual(len(inside), 1)
            stamps.append(time.monotonic())
            time.sleep(0.02)
            inside.pop()
            return 200, OK
        council.http = http
        council._model_cache['nvidia'] = set()
        env = dict(ENV, PF_RETRY_SLEEP='1', PF_PACE_SCALE='0.05')  # nvidia gap 2.0 s x 0.05 = 0.1 s
        threads = [threading.Thread(target=council.complete, args=(SEAT, 'm1', 's', 'u', env)) for _ in range(3)]
        [t.start() for t in threads]
        [t.join() for t in threads]
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        self.assertEqual(len(stamps), 3)
        self.assertTrue(all(g >= 0.09 for g in gaps), gaps)

    def test_every_provider_has_a_pace(self):
        self.assertEqual(set(council.PACE), set(council.PROVIDERS))

    def test_different_providers_are_concurrent_while_each_provider_stays_serial(self):
        active, peak = [], []
        lock = threading.Lock()

        def http(method, url, headers, body=None, timeout=90):
            if url.endswith('/models'):
                return 200, json.dumps({'data': []})
            with lock:
                active.append(url.split('/')[2])
                peak.append(len(active))
            time.sleep(0.03)
            with lock:
                active.pop()
            return 200, OK

        council.http = http
        council._model_cache.clear()
        env = dict(ENV, PF_PACE_SCALE='0')
        groq = dict(SEAT, id='g', provider='groq', models=['g1'])
        threads = [threading.Thread(target=council.complete, args=(SEAT, 'm1', 's', 'u', env)),
                   threading.Thread(target=council.complete, args=(groq, 'g1', 's', 'u', env))]
        [t.start() for t in threads]
        [t.join() for t in threads]
        self.assertGreaterEqual(max(peak), 2, peak)

    def test_convene_lanes_overlap_providers_and_serialize_shared_provider(self):
        original = council.run_seat
        active, max_active, same_provider_overlap = {}, [0], []
        lock = threading.Lock()

        def fake_run(seat, *args):
            provider = seat['provider']
            with lock:
                if active.get(provider):
                    same_provider_overlap.append(provider)
                active[provider] = active.get(provider, 0) + 1
                max_active[0] = max(max_active[0], sum(active.values()))
            time.sleep(0.03)
            with lock:
                active[provider] -= 1
            return {'seat': seat['id'], 'provider': provider, 'status': 'OK', 'answer': {}}

        council.run_seat = fake_run
        try:
            seats = [dict(SEAT, id='a'), dict(SEAT, id='b'),
                     dict(SEAT, id='c', provider='groq', models=['g1'])]
            rows = council.convene(seats, 's', 'u', ENV, None, 'C')
        finally:
            council.run_seat = original
        self.assertEqual([r['seat'] for r in rows], ['a', 'b', 'c'])
        self.assertGreaterEqual(max_active[0], 2)
        self.assertEqual(same_provider_overlap, [])

    def test_account_id_is_checked_and_scrubbed(self):
        acct = 'a' * 32
        env = dict(ENV, CLOUDFLARE_API_TOKEN='cf-FAKE-TOKEN-0009', CLOUDFLARE_ACCOUNT_ID=acct)
        seen = []
        council.http = lambda m, url, h, body=None, timeout=90: (seen.append(url), (200, OK))[1]
        council.complete({'id': 'c', 'provider': 'cloudflare'}, '@cf/x', 's', 'u', env)
        self.assertEqual(seen, ['https://api.cloudflare.com/client/v4/accounts/%s/ai/v1/chat/completions' % acct])
        self.assertEqual(council.scrub('t cf-FAKE-TOKEN-0009 ' + acct, env), 't [key] [key]')
        with self.assertRaises(council.Refused):
            council.complete({'id': 'c', 'provider': 'cloudflare'}, '@cf/x', 's', 'u', dict(env, CLOUDFLARE_ACCOUNT_ID='../x'))
        self.assertIn('api.cloudflare.com', council.allowed_hosts())

    def test_seats_carry_discover_and_keyed_backups_on_other_providers(self):
        cfg = json.loads((ROOT / 'src/council/seats.json').read_text())
        for s in cfg['seats']:
            self.assertTrue(s['discover'], s['id'])
            self.assertTrue(s['backups'], s['id'])
            for b in s['backups']:
                self.assertIn(b['provider'], council.PROVIDERS)
                self.assertNotEqual(b['provider'], s['provider'], s['id'])
        for wf in ('council.yml', 'onboard-review.yml'):
            text = (ROOT / '.github/workflows' / wf).read_text()
            self.assertIn('CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}', text)


if __name__ == '__main__':
    unittest.main()


class AuditMemory(unittest.TestCase):
    def comment(self, prompt='a1650c345e1a', evidence='62c4355fd524', valid=2, when='2026-10-20T00:00:00Z'):
        body = ('<!-- pf-council:audit:selection -->\n1 part(s), 76 file(s) reviewed; %d of 6 seat answers valid from 2 seat(s).\n'
                'prompt sha256 `%s`, evidence sha256 `%s`. Advisory only' % (valid, prompt, evidence))
        return [{'user': {'login': 'github-actions[bot]'}, 'body': body, 'updated_at': when}]

    def ask(self, rows, **kw):
        import datetime
        council.gh = lambda env, method, path, body=None, accept=None: json.dumps(rows)
        args = dict(prompt_hash='a1650c345e1a' + '0' * 52, pack_hash='62c4355fd524' + '0' * 52)
        args.update(kw)
        return council.unchanged_since(dict(ENV), 154, '<!-- pf-council:audit:selection -->', args['prompt_hash'],
                                       args['pack_hash'], now=datetime.datetime(2026, 10, 22, tzinfo=datetime.timezone.utc))

    def test_same_files_and_prompt_recently_audited_is_skipped(self):
        self.assertTrue(self.ask(self.comment()))

    def test_any_difference_audits_again(self):
        self.assertFalse(self.ask(self.comment(evidence='ffffffffffff')))
        self.assertFalse(self.ask(self.comment(prompt='ffffffffffff')))
        self.assertFalse(self.ask(self.comment(valid=0)))
        self.assertFalse(self.ask(self.comment(when='2026-10-01T00:00:00Z')))
        self.assertFalse(self.ask([]))

    def test_read_failure_audits_again(self):
        def boom(*a, **k):
            raise OSError('down')
        council.gh = boom
        self.assertFalse(council.unchanged_since(dict(ENV), 154, 'm', 'a', 'b'))

    def test_incomplete_desk_comment_carries_original_parts_in_order(self):
        comments = [{'user': {'login': 'github-actions[bot]'},
                     'body': '<!-- pf-council:audit:selection -->\n'
                             'Not reviewed (time or part limit): part(s) 4, 2, 4. Run the shard again for them.'}]
        old = council.gh
        try:
            council.gh = lambda *a, **k: json.dumps(comments)
            self.assertEqual(council.audit_carryover(dict(ENV), 154,
                             '<!-- pf-council:audit:selection -->', 5), [4, 2])
            self.assertEqual(council.audit_carryover(dict(ENV), 154,
                             '<!-- pf-council:audit:selection -->', 3), [2])
            self.assertFalse(council.unchanged_since(dict(ENV), 154,
                             '<!-- pf-council:audit:selection -->', 'a', 'b'))
        finally:
            council.gh = old

    def test_forced_and_staged_runs_audit(self):
        council.gh = lambda *a, **k: json.dumps(self.comment())
        for extra in ({'PF_REAUDIT': '1'}, {'PF_COUNCIL_STAGED': '1'}):
            self.assertFalse(council.unchanged_since(dict(ENV, **extra), 154, '<!-- pf-council:audit:selection -->',
                                                     'a1650c345e1a', '62c4355fd524'))
